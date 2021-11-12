#!/usr/bin/env python3
import sys
import os
from datetime import date, datetime, timedelta
import pytz
import logging
from redminelib import Redmine
from envyaml import EnvYAML
from jinja2 import Template
from exceptions import IssueStatusNotFoundException


def get_issue_status_id(status_name: str, redmine: Redmine):
    all_status = redmine.issue_status.all()
    statuses = all_status.filter(name=status_name)
    if len(statuses) < 1:
        raise IssueStatusNotFoundException(status_name)
    elif len(statuses) > 1:
        logging.warning(f'Expected one issue status with the name {status_name} but found '
                        f'{len(statuses)}')
    return statuses[0].id


def treat_issues():
    dir_path = os.path.dirname(os.path.realpath(__file__)) + '/'

    # Set up logging
    logging.basicConfig(
        filename=dir_path + 'marvin.log',
        level=logging.ERROR,
        format='%(asctime)s - %(message)s',
    )

    # Load configuration
    try:
        config = EnvYAML(dir_path + 'config.yaml', dir_path + '.env')
        url = config['redmine']['url']
        version = config['redmine']['version']
        api_key = config['redmine']['api_key']
        time_zone = pytz.timezone(config['redmine']['time_zone'])
        issue_closed_status = config['redmine']['issue_closed_status']
        no_bot_tag = config['redmine']['no_bot_tag']
        actions = config['actions']
        logging.getLogger().setLevel(config['logging']['level'].upper())
    except Exception as e:
        logging.error('Could not load config.yaml', exc_info=True)
        sys.exit(1)

    # Create Redmine object instance
    try:
        redmine = Redmine(url, version=version, key=api_key)
    except Exception as e:
        logging.error('Could not instantiate Redmine object', exc_info=True)
        sys.exit(1)

    # Get status id for closed issues
    issue_closed_status_id = None
    try:
        issue_closed_status_id = get_issue_status_id(issue_closed_status, redmine)
    except IssueStatusNotFoundException as e:
        logging.error(e, exc_info=True)

    # Loop through all actions defined in config.yaml
    for action in actions.values():

        # Calculate end_date
        end_date = date.today() - timedelta(days=+int(action['time_range']))

        # Get change_status_id
        change_status_id = None
        if action.get('change_status_to'):
            try:
                change_status_id = get_issue_status_id(action['change_status_to'], redmine)
            except IssueStatusNotFoundException as e:
                logging.error(e, exc_info=True)
                continue

        # Loop through affected issues
        try:
            for issue in redmine.issue \
                    .filter(updated_on=f"><{action['start_date']}|{end_date.isoformat()}") \
                    .filter(project__name__in=action['projects'], status__name__in=action['status'], closed_on=None):

                # Skip issue if start date is not yet reached
                if hasattr(issue, 'start_date') and date.today() < issue.start_date:
                    logging.info(f'Ticket ID: {issue.id}, skipped because start date not yet reached')
                    continue

                # Skip issue if due date is not yet reached
                if hasattr(issue, 'due_date') and date.today() < issue.due_date:
                    logging.info(f'Ticket ID: {issue.id}, skipped because due date not yet reached')
                    continue

                # Skip issue if a no_bot_tag is found in the issue description or any of its journals
                def find_no_bot_tag_in_journals(journals):
                    for journal in journals:
                        if hasattr(journal, 'notes') and no_bot_tag in journal.notes:
                            return True
                    return False
                if no_bot_tag in issue.description or find_no_bot_tag_in_journals(issue.journals):
                    logging.info(f'Ticket ID: {issue.id}, skipped because no_bot_tag "{no_bot_tag}" was found')
                    continue

                # Render message template
                with open(f"{dir_path}templates/{action['template']}", newline='\r\n') as f:
                    content = f.read()
                template = Template(content)
                days_since_last_update = (datetime.now(time_zone) - issue.updated_on.replace(tzinfo=time_zone)).days + 1
                notes = template.render(
                    issue=issue,
                    time_range=action['time_range'],
                    days_since_last_update=days_since_last_update
                )

                # Update issue
                if action.get('close_ticket') is True and issue_closed_status_id is not None:
                    redmine.issue.update(issue.id, notes=notes, status_id=issue_closed_status_id)
                    logging.info(f"Ticket ID: {issue.id}, ticket closed")
                elif change_status_id is not None:
                    redmine.issue.update(issue.id, notes=notes, status_id=change_status_id)
                    logging.info(f"Ticket ID: {issue.id}, changed ticket status")
                else:
                    redmine.issue.update(issue.id, notes=notes)
                    logging.info(f"Ticket ID: {issue.id}")

        except Exception as e:
            logging.error('Could not process issues', exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    treat_issues()
