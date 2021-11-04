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
    try:
        all_status = redmine.issue_status.all()
        issue_closed_statuses = all_status.filter(name=issue_closed_status)
        if len(issue_closed_statuses) < 1:
            raise IssueStatusNotFoundException(issue_closed_status)
        elif len(issue_closed_statuses) > 1:
            logging.warning(f'Expected one issue status with the name {issue_closed_status} but found '
                            f'{len(issue_closed_statuses)}')
        issue_closed_status_id = issue_closed_statuses[0].id
    except IssueStatusNotFoundException as e:
        logging.error(e, exc_info=True)
        sys.exit(1)

    # Loop through all actions defined in config.yaml
    for action in actions.values():

        # Calculate end_date
        end_date = date.today() - timedelta(days=+int(action['time_range']))

        # Loop through affected issues
        try:
            for issue in redmine.issue \
                    .filter(updated_on=f"><{action['start_date']}|{end_date.isoformat()}") \
                    .filter(project__name__in=action['projects'], status__name__in=action['status'], closed_on=None):

                # Skip issue if a no_bot_tag is found in the issue description or any of its journals
                def find_no_bot_tag_in_journals(journals):
                    for journal in journals:
                        if no_bot_tag in journal.notes:
                            return True
                    return False
                if no_bot_tag in issue.description or find_no_bot_tag_in_journals(issue.journals):
                    continue

                with open(f"{dir_path}templates/{action['template']}", newline='\r\n') as f:
                    content = f.read()
                template = Template(content)
                notes = template.render(
                    issue=issue,
                    time_range=action['time_range'],
                    days_since_last_update=(datetime.now(time_zone) - issue.updated_on.replace(tzinfo=time_zone)).days
                )

                # Update issue
                if action.get('close_ticket') is True:
                    redmine.issue.update(issue.id, notes=notes, status_id=issue_closed_status_id)
                    logging.info(f"Ticket ID: {issue.id}, ticket closed")
                elif action.get('change_status_to') is not None and isinstance(action.get('change_status_to'), int):
                    redmine.issue.update(issue.id, notes=notes, status_id=action['change_status_to'])
                    logging.info(f"Ticket ID: {issue.id}, changed ticket status")
                else:
                    redmine.issue.update(issue.id, notes=notes)
                    logging.info(f"Ticket ID: {issue.id}")

        except Exception as e:
            logging.error('Could not process issues', exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    treat_issues()
