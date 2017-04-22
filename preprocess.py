import psycopg2
from ts_params import *

def ts_db_initialize():
    db_conn = psycopg2.connect("host='/tmp' dbname=%s user=%s password=%s port=%d" % (TS_DB, TS_DB_USER, TS_DB_PASS, TS_DB_PORT))
    # print "Connected To Database"
    return db_conn
    
def ts_db_bubye(db_conn):
    db_conn.close()
    print "Disconnected From Database"

def ts_sql_table_drop(db_conn, table_name):
    cur = db_conn.cursor()
    try:
        cur.execute("DROP TABLE %s" % table_name)
    except psycopg2.Error:
        pass
    db_conn.commit()
    cur.close()

# Drop and recreate table    
def ts_sql_table_drop_create(db_conn, table_name, create_sql_cols, drop=True):
    cur = db_conn.cursor()
    if (drop):
        try:
            cur.execute("DROP TABLE %s" % table_name)
        except psycopg2.Error:
            # Ignore the error
            db_conn.commit()
        
    cur.execute("CREATE TABLE %s (%s)" % (table_name, create_sql_cols));
    db_conn.commit();
    cur.close();
    
# Load table from file 
# TODO: Optimize loading
def ts_sql_load_table_from_file(db_conn, table_name, col_fmt, file_name, delim):
    cur = db_conn.cursor()
    
    cur.execute("COPY %s(%s) FROM '%s' DELIMITER AS '%s' CSV" % (table_name, col_fmt, file_name, delim))
        
    db_conn.commit()
    cur.close()
    # print "Loaded data from %s" % (file_name)

    
db_conn = ts_db_initialize()
ts_sql_table_drop_create(db_conn, 'TS_TABLE_TEMP', 'source_ip text, destination_ip text, time_in_minutes text')
ts_sql_load_table_from_file(db_conn, 'TS_TABLE_TEMP', 'source_ip, destination_ip, time_in_minutes', '/afs/andrew.cmu.edu/usr12/moli/public/826project/data/darpa.csv', ',')

cur = db_conn.cursor()

cur.execute("select sipdiptd from (select sip, dip, td, (sip || ',' || dip || ',' || td) as sipdiptd from (select source_ip sip, destination_ip dip, substring(time_in_minutes from 0 for 11) td from TS_TABLE_TEMP) as tab) as tab2 group by sipdiptd")
result = cur.fetchall()
# print len(result)
for tup in result:
    print tup[0]



