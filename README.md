# Description

This is experimental PMC-Tenant-Updater utility writen in Python3.7

# Workflow

1.	Get auth token from Passport using 3rd party application account credentials
2.	Get list of the tenants to update filtered by CloudServiceID
3.	Iterate over the list of tenant to run updates
4.	Notify on Slack channel #auto_operation about status of eah tenant update

# Run

This is Docker container trigered by WebHook from ADO release.
