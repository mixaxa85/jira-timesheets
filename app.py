from jira import JIRA
import pandas as pd
import dash
from dash import dcc, html, dash_table, Input, Output, State
from dash import callback_context
import dash_bootstrap_components as dbc
from decimal import Decimal, ROUND_HALF_UP
import pytz
import datetime
from datetime import timedelta
import re
import keyring
import os
import json
import numpy as np

#Selecting jira URL, credentials for jira and filters
try:
    with open("assets/var.json") as f:
        var_data = json.load(f)
except KeyError: 
   print ("Can't open the file assets/var.json")
   exit(1)

try:  
   jira_user = var_data['jira_user']
except KeyError: 
   print ("Please set the variable jira_user in var.json")
   exit(1)
try:  
   jira_url_1 = var_data["jira_url_1"]
except KeyError: 
   print ("Please set the variable jira_url_1 in var.json")
   exit(1)

pswrd = keyring.get_password('jira', jira_user)
if pswrd == None:
   print ("Please set your user's password in the keyring by running command 'keyring set jira username'")
   exit(1) 

jira = JIRA(server=jira_url_1, basic_auth=(jira_user, pswrd))

try:  
   jira_url_2 = var_data["jira_url_2"]
   jira_2 = JIRA(server=jira_url_2, basic_auth=(jira_user, pswrd))
except KeyError: 
   jira_2 = None


#Working days
def get_working_days():
    today = datetime.date.today()
    start_of_month = today.replace(day=1)
    working_days = pd.bdate_range(start=start_of_month, end=today).date
    return working_days

def fetch_worklog():
    def fetch_issues(jira_instance, jql_query):
        #Get jira issues by jql
        try:
            return jira_instance.search_issues(jql_query, maxResults=500)
        except Exception as e:
            print(f"Error fetching issues from {jira_instance._options['server']} with query: {jql_query}: {e}")
            return []

    def fetch_worklogs(jira_instance, issue, data, current_month, current_year):
        #Get worklogs for an issue
        try:
            worklogs = jira_instance.worklogs(issue.key)
            for log in worklogs:
                log_date = datetime.datetime.strptime(log.started[:10], "%Y-%m-%d")
                if log.author.name == jira_instance.current_user() and log_date.month == current_month and log_date.year == current_year:
                    data.append({
                        "issue_key": issue.key,
                        "summary": issue.fields.summary,
                        "link": f"{jira_instance._options['server']}/browse/{issue.key}",
                        "user": log.author.displayName,
                        "time_spent": log.timeSpentSeconds,
                        "date": log.started[:10],
                        "worklog_id": log.id,
                        "jira_url": jira_instance._options['server'],
                        "project": issue.fields.project.key,
                    })
        except Exception as e:
            print(f"Error fetching worklogs for issue {issue.key} from {jira_instance._options['server']}: {e}")

    def add_empty_issues(jira_instance, issues, data):
        #Add issues from additional filter ("worklogs" - if exists)
        for issue in issues:
            if issue.fields.project.key != "POWJ":
                data.append({
                    "issue_key": issue.key,
                    "summary": issue.fields.summary,
                    "link": f"{jira_instance._options['server']}/browse/{issue.key}",
                    "user": "",
                    "time_spent": 0,
                    "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "worklog_id": "",
                    "jira_url": jira_instance._options['server'],
                    "project": issue.fields.project.key,
                })

    current_month = datetime.datetime.now().month
    current_year = datetime.datetime.now().year
    data = []

    # JQL-запросы
    jql_query_worklogs = "(worklogAuthor = currentuser() AND worklogDate >= startOfMonth(0) AND worklogDate <= endOfMonth(0))"
    jql_query_empty_issues = ("filter = worklogs and issueFunction not in workLogged('by currentUser() after startOfMonth(0) before endOfMonth(0))')") #additional filter ("worklogs")

    # Delivery Jira
    issues = fetch_issues(jira, jql_query_worklogs)
    for issue in issues:
        if issue.fields.project.key != "POWJ":
            fetch_worklogs(jira, issue, data, current_month, current_year)

    empty_issues = fetch_issues(jira, jql_query_empty_issues)
    add_empty_issues(jira, empty_issues, data)

    # OWS JIRA
    issues_ows = fetch_issues(jira_2, jql_query_worklogs)
    for issue in issues_ows:
        fetch_worklogs(jira_2, issue, data, current_month, current_year)

    empty_issues_ows = fetch_issues(jira_2, jql_query_empty_issues)
    add_empty_issues(jira_2, empty_issues_ows, data)

    # Resulting DataFrame
    return pd.DataFrame(data)

def format_time(seconds):
    if seconds == 0:
        return ""
    hours = Decimal(seconds) / Decimal(3600)
    return f"{hours.quantize(Decimal('0.0'), rounding=ROUND_HALF_UP):.1f}"

def seconds(time_str):
    # Проверяем, является ли входное значение числом
    try:
        numeric_value = float(time_str)
        return int(numeric_value * 3600)  # Возвращаем результат умножения на 3600
    except ValueError:
        pass  # Если это не число, переходим к обработке строки
    
    # Регулярное выражение для форматов Nh, Nm, Nh Nm
    pattern = r'^(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?$'
    match = re.match(pattern, time_str.strip().lower())
    
    if match:
        hours = int(match.group(1)) if match.group(1) else 0  # Часы
        minutes = int(match.group(2)) if match.group(2) else 0  # Минуты
        total_seconds = (hours * 3600) + (minutes * 60)
        return total_seconds
    
    # Если формат не распознан, возвращаем 0
    return 0

def update_table_data():
    global df, df_pivot_time, df_pivot_id, data_table
    try:
        df = fetch_worklog()
        #Add working days to table data
        working_days = get_working_days()
        working_days_set = set(day.strftime('%Y-%m-%d') for day in working_days)
        existing_dates = set(df['date'].unique())
        missing_dates = working_days_set - existing_dates
        for missing_date in missing_dates:
            new_row = {
                "issue_key": ".",
                "summary": "empty",
                "link": "",
                "time_spent": 0,
                "date": missing_date,
                "worklog_id": "",
                "hidden_class": "hidden-row"
            }
            df.loc[len(df)] = new_row

        #Resulting pivot table
        df_pivot = df.pivot_table(
            index=["issue_key", "summary", "link"],
            columns="date",
            values=["time_spent", "worklog_id"],
            aggfunc={"time_spent": "sum", "worklog_id": "max"}
        ).fillna(0)

        #Additional dataframes
        df_pivot_time = df_pivot["time_spent"].apply(lambda col: col.map(format_time)) #To draw a timesheet tables
        df_pivot_id = df_pivot["worklog_id"] #To store worklog IDs

        # Date columns format "dd"
        df_pivot_time.columns = [
            datetime.datetime.strptime(str(col), "%Y-%m-%d").strftime("%d") for col in df_pivot_time.columns
        ]

        df_pivot_time.reset_index(inplace=True)
        df_pivot_id.reset_index(inplace=True)

        data_table = df_pivot_time.to_dict("records")
        columns = [
            {"name": "Key", "id": "link", "editable": False, "presentation": "markdown"},
            {"name": "Ticket", "id": "summary", "editable": False}
        ] + [{"name": col, "id": col} for col in df_pivot_time.columns if col not in ["summary", "link", "issue_key"]]

        # Insert links
        for row in data_table:
            row["link"] = f"[{row['issue_key']}]({row['link']})"

        # Total timespent
        totals = {
            "summary": "", 
            "issue_key": "",
            "link": ""
        }
        for col in df_pivot_time.columns:
            if col not in ["summary", "issue_key", "link"]:
                time_spent_values = df_pivot_time[col].apply(
                    lambda x: float(x) if x != '' and isinstance(x, str) and x.replace('.', '', 1).isdigit() else 0
                )
                totals[col] = round(time_spent_values.sum(), 1)

        data_table.insert(0, totals)

        return df, data_table, columns, df_pivot_time, df_pivot_id

    except Exception as e:
        print(f"Data update error: {e}")
        return None, None

df, data_table, columns, df_pivot_time, df_pivot_id = None, None, None, None, None
df, data_table, columns, df_pivot_time, df_pivot_id = update_table_data()

if data_table is None or columns is None or df_pivot_time is None:
    print("Empty data received")
    data_table = []
    columns = []

#Filters' labels (to show jira tickets by project codes)
project_keys =[]
project_keys.append("All")
for item in var_data["filters"]:
    for filter_label in item:
        project_keys.append(filter_label)

app = dash.Dash(__name__)
app.layout = html.Div([
    html.Div([
    dcc.RadioItems(
        id="project-filter",
        options=[{"label": key, "value": key} for key in project_keys],
        value="All",
        inline=True,
        labelStyle={"margin-right": "10px",'align-items': 'center','display': 'inline-flex','font-size': "13px",'color':'#4d4d4d','font-family':'"Segoe UI", Arial, sans-serif'},
        inputStyle={'width':'30px','height':'30px','border-radius':'50%'}
    ),
    html.Button("Refresh", id="update-button", n_clicks=0, className="btn btn-primary"),], style={'display': 'flex', 'justify-content': 'space-between','align-items': 'flex-end'}),
    html.Link(href="/assets/style.css", rel="stylesheet"),
    dcc.Loading(
        id="loading-indicator",
        overlay_style={"visibility":"visible", "filter": "blur(0px)"},
        type="dot",
        children=[
            dash_table.DataTable(
                id="editable-table",
                data=data_table,
                columns=columns,
                fixed_rows={'headers': True, 'data': 1},
                editable=True,
                hidden_columns=['issue_key'],
                sort_action="native",
                sort_by=[{"column_id": "issue_key", "direction": "asc"}],
                style_header={
                    'fontWeight': 'bold',
                    'background-color': '#333333',
                    'border-style': 'none',
                    'fontSize': '12px',
                    "textAlign": "left",
                    "height": "24px"
                },
                style_table={
                    "overflowY": "scroll",
                    "top": "40px",
                },
                style_data_conditional=[
                    {"if": {"column_id": col},
                    "textAlign": "center",
                    "width": "30px",
                    } for col in df_pivot_time.columns if col not in ["summary", "link"]] + [
                    
                    {"if": {"column_id": col},
                    'props': {'data-value': '{time_spent}'}
                    } for col in df_pivot_time.columns if col not in ["summary", "link"]] + [

                    {"if": {"column_id": "summary"}, 
                    "textAlign": "left", 
                    "width": "400px" 
                    },
                    
                    {
                    "if": {
                        "filter_query": "{summary} = 'empty'",
                        "column_id": "summary"
                    },
                    "height":"0px"
                    },
                ],
            )
        ]),
    dcc.Store(id="log-store", data=""),  #for logs
    html.Div(id="log-container", children=[
        html.Pre(id="riler"),
        html.Pre(id="log-output")
   ], style={
        "width": "100%",
        "marginTop": "80px"
    }),
], style={'display': 'block', 'position': 'absolute', 'top': '200', 'left': '70'}
)

# Data update / filter / refresh
@app.callback(
    [Output("editable-table", "data"), 
     Output("log-store", "data")],
    [Input("project-filter", "value"),
     Input("update-button", "n_clicks"),
     Input("editable-table", "data_previous")],
    State("editable-table", "data"),
    prevent_initial_call=True,
)

def update_worklog(project,n_clicks, data_previous, current_data):
    log_messages = []
    global df, df_pivot_time, df_pivot_id, data_table, delta, time_spent_targ, time_spent_orig
    # Получение контекста вызова
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]  # callback caller

    if triggered_id == "update-button":
        # 1. Data refresh case
        try:
            df, data_table, columns, df_pivot_time, df_pivot_id = update_table_data()
            log_messages.append("Data updated")
            return data_table, "\n".join(log_messages)  # Возвращаем обновлённые данные
        except Exception as e:
            log_messages.append(f"Error fetching data from JIRA: {e}")
            return current_data, "\n".join(log_messages)
    
    elif triggered_id == "project-filter":
        # 2. Data filter case
        filtered_data=[]
        total_row=[]
        if project == "All":
            filtered_data = data_table
        else:
            i=0
            for item in var_data["filters"]:
                for filter_label in item:
                    if filter_label == project: # selected project code
                        if np.array(item[filter_label]).shape[0]==1:
                            project_code = item[filter_label][0]
                            filtered_data = [row for row in data_table if row["issue_key"].startswith(project_code)]
                        if np.array(item[filter_label]).shape[0]==2:
                            project_code = item[filter_label][0]
                            project_code_1 = item[filter_label][1]
                            filtered_data = [row for row in data_table if row["issue_key"].startswith(project_code) or row["issue_key"].startswith(project_code_1)]
                i = i+1

            total_row = {
                "summary": "",
                "issue_key": "",
                "link": ""
            }
            if filtered_data: 
                for col in filtered_data[0].keys():
                    if col not in ["summary", "issue_key", "link"]:
                        try:
                            total_row[col] = round(sum(float(row[col]) for row in filtered_data if row[col]), 1)
                        except ValueError:
                            total_row[col] = ""
            
            filtered_data.append(total_row)

        log_messages.append(f"Filtered by project: {project}")
        
        return filtered_data, "\n".join(log_messages)
    
    elif triggered_id == "editable-table":
        # 3. Data updated
        if data_previous is None:
            return current_data, "\n".join(log_messages)
    
        updated_data = current_data.copy()
        new_totals = {
            "summary": "",
            "issue_key": "",
            "link": ""
        }
        for prev_row, curr_row in zip(data_previous, current_data):
            for col, new_value in curr_row.items():
                if col not in ["summary", "issue_key"] and prev_row[col] != new_value:
                    try:
                        col_index = df_pivot_time.columns.get_loc(col)
                        date_str = df_pivot_id.columns[col_index] #selected date
                        #find existing summarized time_spent for selected issue+date
                        filtered_rows = df.loc[
                            (df["issue_key"] == curr_row["issue_key"]) & 
                            (df["date"] == date_str)
                        ]
                        curr_time_spent = filtered_rows["time_spent"].fillna(0).sum()
                        delta = seconds(new_value) - curr_time_spent
                        #print(f"{curr_time_spent}({curr_time_spent}) -> {seconds(new_value)}; delta={delta}")

                        if delta != 0:
                            if prev_row[col]:  #Case of updating worklog
                                try:
                                    worklog_id = df_pivot_id.loc[(df_pivot_id["issue_key"] == curr_row["issue_key"])][date_str].values[0]
                                    time_spent_orig = df.loc[
                                        (df["issue_key"] == curr_row["issue_key"]) & 
                                        (df["worklog_id"] == worklog_id) & 
                                        (df["date"] == date_str)
                                    ]["time_spent"].values[0]
                                    jira_url = df.loc[
                                        (df["issue_key"] == curr_row["issue_key"]) & 
                                        (df["worklog_id"] == worklog_id) & 
                                        (df["date"] == date_str)
                                    ]["jira_url"].values[0]
                                    if jira_url==jira_url_1:
                                            jira_host = jira
                                    else:
                                            jira_host = jira_2

                                    time_spent_targ = int(time_spent_orig + delta)
                                    worklog = jira_host.worklog(id=worklog_id, issue=curr_row["issue_key"])
                                    worklog.update(timeSpentSeconds=time_spent_targ)
                                    
                                    curr_row[col] = format_time(time_spent_targ) # convert changed cell value to hours
                                    log_messages.append(f"Worklog {worklog_id} for ticket {curr_row['issue_key']} updated successfully: {time_spent_orig} -> {time_spent_targ}")                        
                                    df.loc[ #update initial dataframe
                                        (df["issue_key"] == curr_row["issue_key"]) & 
                                        (df["worklog_id"] == worklog_id) & 
                                        (df["date"] == date_str), 
                                        "time_spent"
                                    ] = time_spent_targ

                                except Exception as e:
                                    log_messages.append(f"Failed to update worklog: ticket {curr_row['issue_key']}, {time_spent_orig} -> {time_spent_targ}: {e}")
                                    updated_data[updated_data.index(curr_row)][col] = prev_row[col]

                            else:  #Case of registering a new worklog
                                try:
                                    time_spent_targ = delta
                                    started_datetime = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(hour=9, minute=0, second=0, microsecond=0)
                                    started_datetime = pytz.utc.localize(started_datetime)
                                    jira_url = df.loc[
                                        (df["issue_key"] == curr_row["issue_key"])
                                    ]["jira_url"].values[0]
                                    if jira_url==jira_url_1:
                                            jira_host = jira
                                    else:
                                            jira_host = jira_2
                                    worklog = jira_host.add_worklog(issue=curr_row["issue_key"], timeSpent=f"{time_spent_targ/3600:.4f}h", started=started_datetime)
                                    worklog_id = worklog.id
                                    new_row = {
                                        "issue_key": curr_row["issue_key"],
                                        "summary": curr_row["summary"],
                                        "link": curr_row["link"],
                                        "time_spent": time_spent_targ,
                                        "date": date_str,
                                        "worklog_id": worklog_id,
                                        "jira_url": jira_url
                                    }
                                    df.loc[len(df)] = new_row  # update initial dataframe

                                    # update worklog list
                                    if date_str not in df_pivot_id.columns:
                                        df_pivot_id[date_str] = None 
                                    df_pivot_id.loc[df_pivot_id["issue_key"] == curr_row["issue_key"], date_str] = worklog_id
                                    #print(f"{time_spent_targ}")
                                    #print(f"{time_spent_targ} -> {time_spent_targ/3600:.1f}")
                                    curr_row[col] = f"{time_spent_targ/3600:.1f}" # convert changed cell value to hours
                                    log_messages.append(f"Worklog for ticket {curr_row['issue_key']} on {date_str} registered")
                                except Exception as e:
                                    print(f"Failed to add worklog: {e}")
                                    updated_data[updated_data.index(curr_row)][col] = prev_row[col]
                    # Totals recalculate
                        if col not in ["summary", "issue_key", "link"]:
                            time_spent_values = pd.Series([float(row[col]) if isinstance(row[col], str) and row[col].replace('.', '', 1).isdigit() else 0 for row in current_data])
                            new_totals[col] = round(time_spent_values.sum(), 1)

                    except Exception as e:
                        log_messages.append(f"Error updating worklog: {e}")
                        updated_data[updated_data.index(curr_row)][col] = prev_row[col]

        # Record with totals update
        for row in current_data:
            if row["issue_key"] == "":
                row.update(new_totals)

        return current_data, "\n".join(log_messages)

    return current_data, "\n".join(log_messages)

@app.callback(
    Output("log-output", "children"),
    Input("log-store", "data")
)
def display_logs(log_data):
    return log_data

if __name__ == "__main__":
    app.run_server(debug=True)
