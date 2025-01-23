# Jira Timesheets
The easiest way to manage your daily worklogs

You can add/modify your worklogs in several jira instances right in the table form - like in Excel table:

![Image alt](https://github.com/mixaxa85/jira-timesheets/blob/main/JiraTS.png)

Note: at the moment, the toolkit tested only on MacOS

## Installation

Create configuration file **assets/var.json** with following format

```
{
        "filters": [
            {"<filter label 1>": ["<jira project 1 key>"]},
            {"filter label 2": ["<jira project 2 key>"]}
            ],
        "jira_user" : "<your jira user>",
        "jira_url_1": "<your first jira instance URL>",
        "jira_url_2": "<optionally set your second jira instance URL>"
}
```

For example:

```
{
        "filters": [
            {"Support": ["SUP"]},
            {"Implementation": ["IMPL"]},
            {"Internal": ["INT"]},
            {"SME": ["ARCH","BA"]}
            ],
        "jira_user": "elon_mask",
        "jira_url_1": "https://jira.google.com>",
        "jira_url_2": "https://jira.amazon.com"
}
```

Set your jira credentials:

```
Open Terminal app
>> pip install keyring
>> keyring set jira <your jira username>
```
