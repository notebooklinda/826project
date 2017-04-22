import psycopg2
from ts_params import *

def ts_db_initialize():
    db_conn = psycopg2.connect("host='/tmp' dbname=%s user=%s password=%s port=%d" % (TS_DB, TS_DB_USER, TS_DB_PASS, TS_DB_PORT))
    print "Connected To Database"
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
def ts_sql_load_table_from_file(db_conn, table_name, col_fmt, file_name, delim):
    cur = db_conn.cursor()
    
    cur.execute("COPY %s(%s) FROM '%s' DELIMITER AS '%s' CSV" % (table_name, col_fmt, file_name, delim))
        
    db_conn.commit()
    cur.close()
    print "Loaded data from %s" % (file_name)


def ts_sql_add_default_measure(db_conn, table_name, measure_name):
    cur = db_conn.cursor()
    cur.execute("ALTER TABLE %s ADD COLUMN %s REAL DEFAULT 1.0" %(table_name, measure_name))    
    db_conn.commit()
    cur.close()
    print "Add a measure attribute named %s" % (measure_name) 


def ts_sql_add_keep(db_conn, table_name):
    cur = db_conn.cursor()
    cur.execute("ALTER TABLE %s ADD COLUMN %s Boolean DEFAULT True" % (table_name, 'keep'))    
    db_conn.commit()
    cur.close()
    print "Added keep column"
