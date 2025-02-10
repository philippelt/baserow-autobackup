export BASEROW_USER=<baserow username>
export BASEROW_PWD=<baserow password>
export BASEROW_EMAIL=<baserow email>
export BASEROW_API_URL=https://<your.baserow.host>/api/

# You can use autobackup on baserow as a service on the official platform, just define
# export BASEROW_API_URL=https://baserow.io/api/
# All backup data will stay on the baserow saas platform into your account


./cli_backup.py "$@"

# Example use: List backups of database 225 (from project X)
# ./cli_backup.sh 225 list
#
# Example use: Create an Autobackup for database 225 and keep the last 5 autobackups
# ./cli_backup.sh 225 take
# ./cli_backup.sh 225 purge 5

# The purge action as no effect on backups which name do not start with "Autobackup..."
# but the baserow backup quota includes all backups whether auto or done using baserow UI.
