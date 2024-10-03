export BASEROW_USER=<baserow username>
export BASEROW_PWD=<baserow password>
export BASEROW_EMAIL=<baserow email>
export BASEROW_API_URL=https://<your.baserow.host>/api/

./cli_backup.py $@

# Example use: List backups of database 225 (from project X)
# ./clibackup.sh 225 list
#
# Example use: Create an Autobackup for database 225
# ./clibackup.sh 225 take
