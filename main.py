#!/usr/bin/env python3
import sys
import os
from datetime import date, timedelta
import logging
from redminelib import Redmine
from envyaml import EnvYAML
from jinja2 import Template


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
        config = EnvYAML(dir_path + 'config.yaml')
        url = config['redmine']['url']
        version = config['redmine']['version']
        api_key = config['redmine']['api_key']
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

    # Loop through all actions defined in config.yaml
    for action in actions.values():

        # Calculate end_date
        end_date = date.today() - timedelta(days=+int(action['time_range']))

        # Loop through affected issues
        try:
            for issue in redmine.issue \
                    .filter(updated_on=f"><{action['start_date']}|{end_date.isoformat()}") \
                    .filter(project__name__in=action['projects'], status__name__in=action['status'], closed_on=None):
                with open(f"{dir_path}templates/{action['template']}", newline='\r\n') as f:
                    content = f.read()
                template = Template(content)
                notes = template.render(author=issue.author.name, time_range=action['time_range'], url=issue.url)

                # Update issue
                if action.get('close_ticket') is True:
                    redmine.issue.update(issue.id, notes=notes, status_id=config['redmine']['issue_closed_id'])
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
