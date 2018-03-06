import bugzilla
import pandas as pd
from datetime import datetime
import urllib.parse as urlparse

URL = "bugzilla.mozilla.org"
BZ_COMPONENTS = [
    "WebExtensions: Android",
    "WebExtensions: Compatibility",
    "WebExtensions: Developer Tools",
    "WebExtensions: Experiments",
    "WebExtensions: Frontend",
    "WebExtensions: General",
    "WebExtensions: Request Handling",
    "WebExtensions: Storage",
    "WebExtensions: Themes",
    "WebExtensions: Untriaged"
]

bzapi = bugzilla.Bugzilla(URL)

def is_core_platform(disabled_on):
    return disabled_on.lower().find("windows") >= 0 or disabled_on.lower().find("all") >= 0

def format_see_also(see_also):
    out = []
    for link in see_also:
        if link.startswith("https://bugzilla.mozilla.org/show_bug.cgi?id="):
            bugid = urlparse.parse_qs(urlparse.urlparse(link).query)["id"][0]
            out += ["<a href='%s'>%s</a>" % (link, bugid)]
        else:
            out += ["<a href='%s'>%s</a>" % (link, link)]
    return ", ".join(out)
            

def format_disabled_on(disabled_on):
    if is_core_platform(disabled_on):
        return "<b style='background: red; color: white; padding: 2px;'>%s</b>" % disabled_on
    elif disabled_on == "-":
        return "<b style='background: yellow;'>%s</b>" % disabled_on
    return disabled_on

def report_webext_disabled_intermittents():
    ## Loads Bob's spreadsheet into a DataFrame and index it by bug number.
    csvDf = pd.read_csv("notes.csv")
    csvDf["id"] = csvDf["Bug Number"]
    csvDf = csvDf.set_index("id")

    display('Number of notes related to disabled intermittents loaded from csv: %d' % len(list(csvDf.index)))
    
    query = bzapi.build_query(product="toolkit", component=BZ_COMPONENTS)
    query["keywords"] = "intermittent-failure"
    query["whiteboard"] = "disabled"
    query["is_open"] = True

    bugs = bzapi.query(query)

    display('Number of disabled intermittents found on bugzilla: %d' % len(bugs))

    ## Convert bugzilla query results into pandas DataFrame and prepare it to be joined
    ## with the DataFrame loaded from the csv file.
    df = pd.DataFrame.from_dict([bug.__dict__ for bug in bugs])
    
    # Set the index to the bug number (same as the DataFrame loaded from the csv file),
    # and join the two DataFrames.
    df = df.set_index("id")
    df = df.join(csvDf)
    
    # Duplicate the bug id column (to render it as an HTML link in the final rendered table)
    df["&#x1F517;"] = list(df.index);
    
    df["Core Platform"] = df["Disabled on"].map(is_core_platform)
    
    # Select the set of columns to render.
    df = df.loc[:, [
       "&#x1F517;",
       "Test", "summary", "status",
       "priority",
       "Disabled on", "Core Platform",
       "whiteboard", 
       "assigned_to",
       "see_also",
       "last_change_time"
    ]]
    
    ## Use the summary where the Test column from the csv is empty.
    df["Test"] = df["Test"].fillna(df["summary"])
    df.drop('summary', axis=1, inplace=True)

    # Clean any nobody and remove the domain from the email addresses.
    df["assigned_to"] = df["assigned_to"].map(lambda x: "-" if x == "nobody@mozilla.org" else x.split("@")[0])

    ## Convert xmlrpc datetime object to string (to be able to sort by it).
    df["last_change_time"] = df["last_change_time"].map(lambda x: "%s" % x)

    ## Sort the table, fill any gap and format some columns for the final table rendering.
    table = df.sort_values(
        by=["priority", "Core Platform", "last_change_time"], ascending=[True, False, True]
    ).fillna("-").style.format({
        "&#x1F517;": lambda x: "<a href='https://bugzilla.mozilla.org/%s'>&#x1F517;</a>" % x,
        "see_also": format_see_also,
        "Disabled on": format_disabled_on,
    })
    
    display("Last generated: %s" % datetime.today())
    
    display(table)