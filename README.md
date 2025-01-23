# Jira Timesheets
The easiest way to manage your daily worklogs.

You can add/modify your worklogs in several jira instances right in the table form - like in Excel

## Features

Jira Timesheets selects jira issues by the following two JQLs via jira API, and represents the resulting data in the web-form:

```
1. (worklogAuthor = currentuser() AND worklogDate >= startOfMonth(0) AND worklogDate <= endOfMonth(0))
2. filter = worklogs
```

![Image alt](https://github.com/mixaxa85/jira-timesheets/blob/main/JiraTS.png)

Now you can add new worklog or update an existing one by just a double-click in a table cell. The application automatically registers/updates a worklog once the new value has been set.

You can set spent time either in hours in **decimals** (1.5) or in jira-like format (e.g. **1h 45m**).

You can optionally (see instructions below):

 - configure interaction with two separate jira instances - by setting **jira_url_2** in configuration file,

 - set filters list (e.g. "Support tickets" / "Development") - to filter the list based on jira projects with specified keys.

**Refresh** button - just reads all the actual data from jira (in case you have updated something in jira and want to refresh the dataform).

**Note**: the application was tested with Jira Server and MacOS only


## Installation

### Jira
By default, the application will read your worklogs registered in current month. You can additionally create a JQL filter with name **worklogs** (hardcoded) - with tickets that you want to be shown in addition.

### Create configuration file **assets/var.json** with following format

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

### Set your jira credentials in keyring:

It will store your password securily in macOS Keychain / Windows Credential Locker - see https://pypi.org/project/keyring/

```
Open Terminal app
>> pip install keyring
>> keyring set jira <your jira username>
```

### Run the application

It will start dash-server

```
>> python app.py
```

### Open TimeSheets web-page

URL - http://127.0.0.1:8050
