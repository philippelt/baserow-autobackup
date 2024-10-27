# Baserow Auto-backup tool

Baserow provides user with backup capability for databases and applications. This feature is accessible in the database menu (3 dots on the right of database name).

Users can create backup, giving them names to retrieve them easily and restore any backup (as a clone of the original database or app).

The issue is that users frequently **forget** to create backups regularly by hand and discover that they don't have a backup when they make a mistake.

This tools will provide the cabability to automate these backups without user intervention.

There are two flavor of the tools:
- In the kubernetes subdir, everything required to run the backup tool periodically in a kubernetes environment
- In the manual subdir, an interactive tool that can also be called from regular scripts run as cron jobs

The tools are python based. The only dependency for the interactive tool is the `requests` library. You can install it using `pip3 install requests` or `apt install python3-requests` if you are using debian or ubuntu.

Interactive usage is easy like, for example :

- `./cli_backup.sh 229 list` to list all available backups for the database 229 (manual and auto backups)
- `./cli_backup.sh 229 take` to create a backup copy of the 229 database Id with the default label `Autobackup <date-time>`
- `./cli_backup.sh 229 purge 5` will keep only the last 5 auto-backups

The database Id will be found, when looking at the database menu, between parentheses at the top of the menu.

All created backups are similar to manually created backups and accessible the same way. The are named `Autobackup <date-time>`.

>Note: There is a limit in the number of backups per project and if a project is using multiples DBs the total numbers of backup can reach the limit. For this reason, the default retention property (global) can be customized at each project level in the kubernetes config map.

### Changes:  
- Kubernetes : Added retention parameter at project level to deal with baserow backup limit per project
- CLI : Added purge function to keep only last n auto-backups and delete olders
- Both : Added Job status polling to detect backup completion rather than using timer