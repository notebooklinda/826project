from ts_sql import *
from ts_params import *
import sys
import argparse
from copy import deepcopy
import numpy as np


def d_cube(db_conn, k, density, dim_attr, measure_attr):
    cur = db_conn.cursor()

    # copy R to Rori
    ts_sql_table_drop(db_conn, TS_TABLE_COPY)
    cur.execute("CREATE TABLE %s AS SELECT * FROM %s" % (TS_TABLE_COPY, TS_TABLE))
    db_conn.commit()

    RN = []
    for col in dim_attr:
        cur.execute("SELECT distinct %s FROM %s" % (col, TS_TABLE_COPY))
        Rn_list = cur.fetchall()
        Rn = {key:None for (key,) in Rn_list}
        RN.append(Rn)

    result_names = []
    for i in range(k):
        cur.execute("SELECT sum(%s) FROM %s" % (measure_attr, TS_TABLE_COPY))
        mass_R = cur.fetchone()[0]
        BN = find_single_block(db_conn, TS_TABLE_COPY, RN, mass_R, 'ari', dim_attr, measure_attr)
        # BN = [[('A1YS9MDZP93857',), ('A3TS466QBAWB9D',)],
              # [('0006428320',), ('0014072149',)],
              # [('1394496000',), ('1370476800',)]]
        
        
        # deleting condition:
        
        ## debug
        # print '#### before ####'
        # cur.execute("SELECT * FROM TS_TABLE_COPY")
        # print cur.fetchall()
        ## debug
        
        to_delete = []
        for col, Bn in zip(dim_attr, BN):
            to_delete.append('%s in (%s)' % (col, ', '.join(("'%s'" % n) for n in Bn)))
        where_clause = ' '.join(['WHERE', ' AND '.join(to_delete)])
        
        cur.execute("DELETE FROM %s %s" % (TS_TABLE_COPY, where_clause))
        db_conn.commit()
        
        ## debug
        # print '#### after ####'
        # cur.execute("SELECT * FROM TS_TABLE_COPY")
        # print cur.fetchall()
        ## debug
        
        result_table = TS_RESULT + str(i)
        result_names.append(result_table)
        ts_sql_table_drop(db_conn, result_table)

        cur.execute("CREATE TABLE %s AS SELECT * FROM %s %s" % (result_table, TS_TABLE, where_clause))
        db_conn.commit()
        
    
    for i in range(k):
        print '#### result ####'
        cur.execute("SELECT * FROM TS_RESULT%d" %(i))
        print cur.fetchall()
    
    ## debug
    # print '#### result ####'
    # cur.execute("SELECT * FROM TS_RESULT0")
    # print cur.fetchall()
    ## debug
        
            # cur.execute("SELECT * FROM TS_TABLE_COPY")
            # print cur.fetchall()
            # cur.execute("DELETE FROM %s WHERE %s in (%s)" % (TS_TABLE_COPY, col, to_delete))
            # db_conn.commit()
            # cur.execute("SELECT * FROM TS_TABLE_COPY")
            # print cur.fetchall()
            # import pdb; pdb.set_trace()

    db_conn.commit()
    cur.close()

def find_single_block(db_conn, table_name, RN, mass_R, density_type, dim_attr, measure_attr):
    cur = db_conn.cursor()

    # copy R to B
    ts_sql_table_drop(db_conn, TS_TABLE_B)
    cur.execute("CREATE TABLE %s AS SELECT * FROM %s" % (TS_TABLE_B, table_name))
    db_conn.commit()
    mass_B = mass_R
    BN = deepcopy(RN)
    rho_tilda = density(mass_B, BN, mass_R, RN, density_type)
    r, r_tilda = 1, 1
    order = [{} for _ in range(len(dim_attr))]
    
    
    while sum(len(Bn) for Bn in BN):
        print sum(len(Bn) for Bn in BN)
        # import pdb; pdb.set_trace()
        mass_BN = [{} for _ in RN]
        for i, Rn in enumerate(RN): 
            for name in Rn:
                mass_BN[i][name] = 0.0
        
        for i, col in enumerate(dim_attr):
            cur.execute("SELECT %s, sum(%s)" % (col, measure_attr) +
                        " FROM %s" % TS_TABLE_B +
                        " GROUP BY %s" % col)
            mass_Bn_list = cur.fetchall()
            for name, mass in mass_Bn_list:
                mass_BN[i][name] = mass

        
        idx = select_dimension_by_cardinality(BN)
        # idx = select_dimension_by_density(BN, RN, mass_BN, mass_B, mass_R, 'ari')
        mass_avg = mass_B / float(len(BN[idx]))
        
        BN_idx_list = BN[idx].keys()
        mass_i_array = np.array([mass_BN[idx][n] for n in BN_idx_list])
        
        D_idx = np.where(mass_i_array <= mass_avg)[0]
        Di = [BN_idx_list[i] for i in D_idx]
        Di_sorted_idx = np.argsort([mass_BN[idx][n] for n in Di])
        Di_sorted = [Di[i] for i in Di_sorted_idx]
        
        # import pdb; pdb.set_trace()
        
        for n in Di_sorted:
            BN[idx].pop(n)
            mass_B -= mass_BN[idx][n]
            rho_prime = density(mass_B, BN, mass_R, RN, density_type)
            order[idx][n] = r
            r += 1
            if rho_prime > rho_tilda:
                rho_tilda = rho_prime
                r_tilda = r
        
        
        attr_set = ', '.join(''.join(["'", n, "'"]) for n in Di_sorted)
        condition = ' '.join([dim_attr[idx], 'in (', attr_set, ')'])
        
        # print '#### before ####'
        # cur.execute("SELECT * FROM TS_TABLE_B")
        # print cur.fetchall()
        
        # import pdb; pdb.set_trace()
        
        
        if len(condition):
            cur.execute("DELETE FROM %s WHERE %s" % (TS_TABLE_B, condition))
        db_conn.commit()
        
        # print '#### after ####'
        # cur.execute("SELECT * FROM TS_TABLE_B")
        # print cur.fetchall()
        
        # import pdb; pdb.set_trace()
        # BN = []
        # for col in dim_attr:
            # cur.execute("SELECT distinct %s FROM %s" % (col, TS_TABLE_B))
            # BN.append(cur.fetchall())
    
    
    db_conn.commit()
    cur.close()
    
    #import pdb; pdb.set_trace()
    B_tilda_N = []
    for i, Rn in enumerate(RN):
        B_tilda_n = []
        for name in Rn.iterkeys():
            if order[i][name] >= r_tilda:
                B_tilda_n.append(name)
        B_tilda_N.append(B_tilda_n)
    return B_tilda_N

    
def density(mass_B, BN, mass_R, RN, option):
    if option == 'ari':
        total = sum(len(Bn) for Bn in BN)
        result = 0.0 if not total else mass_B/(float(total)/len(BN))
    elif option == 'geo':
        prod = np.prod([float(len(Bn)) for Bn in BN])
        result = mass_B/prod**(1.0/len(BN)) 
    elif option == 'susp':
        ratio = np.prod([float(len(Bn))/len(Rn) for Bn, Rn in zip(BN, RN)])
        result = mass_B * (np.log(mass_B/mass_R) - 1) + mass_R * ratio - mass_B * np.log(ratio)
    else: 
        raise Exception('wrong density measure input')
    return result
    
def select_dimension_by_cardinality(BN):
    return np.argmax([len(Bn) for Bn in BN])


def select_dimension_by_density(BN, RN, mass_BN, mass_B, mass_R, density_type):
    rho_tilda = -np.inf
    i_tilda = 1
    BN_prime = deepcopy(BN)
    
    for idx in range(len(BN)):
        BN_idx_list = BN[idx].keys()
        if len(BN_idx_list):
            mass_avg = mass_B / float(len(BN_idx_list))
        
            try:
                mass_i_array = np.array([mass_BN[idx][n] for n in BN_idx_list])
            except:
                import pdb; pdb.set_trace()
        
            D_idx = np.where(mass_i_array <= mass_avg)[0]
            Di = [BN_idx_list[i] for i in D_idx]
            
            total = 0
            for n in Di:
                #import pdb; pdb.set_trace()
                BN_prime[idx].pop(n)
                total += mass_BN[idx][n]
            mass_B_prime = mass_B - total
            
            BN_new = deepcopy(BN)
            BN_new[idx] = BN_prime[idx]
            rho_prime = density(mass_B_prime, BN_new, mass_R, RN, density_type)
            
            if rho_prime > rho_tilda:
                rho_tilda = rho_prime
                i_tilda = idx
    
    return i_tilda

      

def main():
    global db_conn
    db_conn = None
    parser = argparse.ArgumentParser(description="Find dense blocks by Dcube")
    parser.add_argument ('--file', dest='input_file', type=str, required=True,
                         help='Full path to the file to load from. For weighted \
                         graphs, the file should have the format (<src_id>, <dst_id>, <weight>) \
                         . If unweighted please run with --unweighted option. To specify a \
                         delimiter other than "," (default), use --delim option. \
                         NOTE: The file should have proper permissions set for \
                         the postgres user.' 
                         )                         
    parser.add_argument ('--delim', dest='delimiter', type=str, default=',',
                         help='Delimiter that separate the columns in the input file. default ","')
    parser.add_argument ('--colname', dest='colname', type=str, default=None,
                         help='Column names. default None')
    parser.add_argument ('--measure_attr', dest='measure_attr_idx', type=int, default=None,
                         help='Find which column is measure attribute. default None')
    parser.add_argument ('--num_dense_blocks', dest='num_dense_blocks', type=int, default=1,
                         help='Number of dense blocks. default 1')

                         
    args = parser.parse_args()
    with open(args.input_file) as csv:
        line = csv.next()
        dim = len(line.strip().split(args.delimiter))
    
    if args.colname is None:
        colname = [['dim{:d}'.format(d), 'text'] for d in range(dim)]
    else:
        colname = args.colname.split(' ')
        colname = [[name, 'text'] for name in colname]
        assert len(colname) == dim
    
    if args.measure_attr_idx is not None:
        colname[args.measure_attr_idx][1] = 'real'
        measure_attr = colname[args.measure_attr_idx][0]
    else:
        measure_attr = DEF_MEASURE
    
    dim_attr = [n for n, t in colname if t == 'text']

    colnametype = ', '.join(' '.join([n, t]) for n, t in colname)
    colname = ', '.join(n for n, t in colname)
    
    
    # Run the various graph algorithm below
    try:
        db_conn = ts_db_initialize()
        ts_sql_table_drop_create(db_conn, TS_TABLE, colnametype, drop=True)
        ts_sql_load_table_from_file(db_conn, TS_TABLE, colname, args.input_file, args.delimiter)
        if args.measure_attr_idx is None:
            ts_sql_add_default_measure(db_conn, TS_TABLE, DEF_MEASURE)
        
        d_cube(db_conn, args.num_dense_blocks, None, dim_attr, measure_attr)
        
        # cur = db_conn.cursor()
        # cur.execute('SELECT * from %s' % TS_TABLE)
        # print(cur.fetchall())
        ts_db_bubye(db_conn)
        
    except:
        print "Unexpected error:", sys.exc_info()[0]    
        if (db_conn):
            ts_db_bubye(db_conn)            
        raise                    

        

        
if __name__ == '__main__':
    main()
    
