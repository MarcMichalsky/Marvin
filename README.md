# Marvin
Marvin is a bot for Redmine. He helps you to tidy up your ticket system by nudging and/or closing abandoned tickets.

## Configuration
After pulling the repository you have to fulfill the requirements with:
```bash
pip3 install -r requirements
```
Next copy the example files, rename them to `.env` and `config.yaml` and fill in the right values.

### Configure actions
You can define different actions for the bot to perform.  
Below the `actions` section in the `config.yaml` you can add your own actions.

```yaml
actions:

  waiting_for_feedback:
    start_date: "2021-01-01"  # Date from which tickets are to be processed (all tickets from yyyy-mm-dd)
    time_range: "14"  # Number of days that should be exceeded without updates on the ticket
    projects:
      - "IT Tickets"  # List of redmine projects
    status:
      - "Waiting for feedback"  # List of all issue status you want to treat
    close_ticket: true  # Should the ticket be closed after the update?
    template: "close_ticket" # Template for the update massage

  in_revision:
    start_date: "2021-01-01"
    time_range: "14"
    projects:
      - "IT Tickets"
    status:
      - "In revision"
    close_ticket: false
    template: "nudge_ticket"
```

## Usage
To run the script at regular intervals, simply add it to the crontab.  

Open crontab
```bash
crontab -e
```

Add entry
```
30 8 * * * python3 path/to/main.py
```
This executes the script every day at 8.30 am.

