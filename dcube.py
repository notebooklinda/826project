from ts_sql import *
from ts_params import *
import sys
import argparse
from copy import deepcopy
import numpy as np
import time

def d_cube(db_conn, k, dim_attr, measure_attr, density_type, selection_policy, copy_table):
    cur = db_conn.cursor()

    # copy R to Rori
    ts_sql_table_drop(db_conn, TS_TABLE_COPY)
    cur.execute("CREATE TABLE %s AS SELECT * FROM %s" % (TS_TABLE_COPY, TS_TABLE))
    db_conn.commit()

    RN = []
    for col in dim_attr:
        cur.execute("SELECT distinct %s FROM %s" % (col, TS_TABLE))
        Rn_list = cur.fetchall()
        Rn = {key:None for (key,) in Rn_list}
        RN.append(Rn)

    result_names = []
    density_blocks = []
    length_blocks = []
    for i in range(k):
        cur.execute("SELECT sum(%s) FROM %s" % (measure_attr, TS_TABLE))
        mass_R = cur.fetchone()[0]
        BN = find_single_block(db_conn, TS_TABLE, RN, mass_R, density_type, dim_attr, measure_attr, selection_policy, copy_table)
        
        to_delete = []
        for col, Bn in zip(dim_attr, BN):
            to_delete.append('%s in (%s)' % (col, ', '.join(("'%s'" % n) for n in Bn)))
        where_clause = ' '.join(['WHERE', ' AND '.join(to_delete)])
        
        cur.execute("DELETE FROM %s %s" % (TS_TABLE, where_clause))
        db_conn.commit()
        
        result_table = TS_RESULT + str(i)
        result_names.append(result_table)
        ts_sql_table_drop(db_conn, result_table)

        cur.execute("CREATE TABLE %s AS SELECT * FROM %s %s" % (result_table, TS_TABLE_COPY, where_clause))
        db_conn.commit()
        
        cur.execute("SELECT sum(%s) FROM %s" % (measure_attr, result_table))
        mass_B = cur.fetchone()[0]
        density_B = density(mass_B, BN, mass_R, RN, density_type)
        density_blocks.append(density_B)
        
        
        cur.execute("SELECT * FROM %s" %(result_table))
        length_blocks.append(len(cur.fetchall()))

    db_conn.commit()
    cur.close()
    return density_blocks, length_blocks

def find_single_block(db_conn, table_name, RN, mass_R, density_type, dim_attr, measure_attr, selection_policy, copy_table):
    cur = db_conn.cursor()

    if copy_table:
        print 'Copy %s to %s in find_single_block' % (table_name, TS_TABLE_B)
        # copy R to B
        ts_sql_table_drop(db_conn, TS_TABLE_B)
        # cur.execute("CREATE TABLE %s AS SELECT * FROM %s" % (TS_TABLE_B, table_name))
        
        cur.execute("CREATE TABLE %s (LIKE %s INCLUDING ALL)" % (TS_TABLE_B, table_name))
        db_conn.commit()
        cur.execute("INSERT INTO %s SELECT * FROM %s" % (TS_TABLE_B, table_name))
        use_as_B = TS_TABLE_B
    else:
        print 'Mark keep to True or False in %s' % table_name
        # set R's keep to all True
        cur.execute("UPDATE %s SET keep = True" % table_name)
        use_as_B = table_name
    db_conn.commit()

    mass_B = mass_R
    BN = deepcopy(RN)
    rho_tilda = density(mass_B, BN, mass_R, RN, density_type)
    r, r_tilda = 1, 1
    order = [{} for _ in range(len(dim_attr))]
    
    mass_RN = [{} for _ in RN]
    for i, col in enumerate(dim_attr):
        cur.execute("SELECT %s, sum(%s)" % (col, measure_attr) +
                    " FROM %s" % use_as_B +
                    " WHERE keep = True" +
                    " GROUP BY %s" % col)
        mass_Rn_list = cur.fetchall()
        for name, mass in mass_Rn_list:
            mass_RN[i][name] = mass
    
    while sum(len(Bn) for Bn in BN):
        print sum(len(Bn) for Bn in BN)
        mass_BN = [{} for _ in RN]
        for i, Rn in enumerate(RN): 
            for name in Rn:
                mass_BN[i][name] = 0.0
        
        for i, col in enumerate(dim_attr):
            cur.execute("SELECT %s, sum(%s)" % (col, measure_attr) +
                        " FROM %s" % use_as_B +
                        " WHERE keep = True" +
                        " GROUP BY %s" % col)
            mass_Bn_list = cur.fetchall()
            for name, mass in mass_Bn_list:
                mass_BN[i][name] = mass

        if selection_policy == 'cardinality':
            idx = select_dimension_by_cardinality(BN)
        elif selection_policy == 'density':
            idx = select_dimension_by_density(BN, RN, mass_BN, mass_B, mass_R, density_type)
        else:
            raise Exception('wrong selection policy')
        denom = float(len(BN[idx]))
        mass_avg = mass_B if not denom else mass_B / float(len(BN[idx]))
        
        BN_idx_list = BN[idx].keys()
        mass_i_array = np.array([mass_BN[idx][n] for n in BN_idx_list])

        D_idx = np.where(mass_i_array <= mass_avg + 1e-5)[0]
        Di = [BN_idx_list[i] for i in D_idx]
        Di_sorted_idx = np.argsort([mass_BN[idx][n] for n in Di])
        Di_sorted = [Di[i] for i in Di_sorted_idx]

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

        if attr_set != '':
            if copy_table:
                cur.execute("DELETE FROM %s WHERE %s" % (TS_TABLE_B, condition))
            else:
                cur.execute("UPDATE %s SET keep = False WHERE %s" % (table_name, condition))
        db_conn.commit()

    db_conn.commit()
    cur.close()

    B_tilda_N = []
    for i, Rn in enumerate(RN):
        B_tilda_n_list = []
        for name in Rn.iterkeys():
            if order[i][name] >= r_tilda:
                B_tilda_n_list.append(name)
        B_tilda_n = {key:None for key in B_tilda_n_list}
        B_tilda_N.append(B_tilda_n)
    
    return B_tilda_N
    
def density(mass_B, BN, mass_R, RN, option):
    if option == 'ari':
        total = sum(len(Bn) for Bn in BN)
        result = 0.0 if not total else mass_B/(float(total)/len(BN))
    elif option == 'geo':
        prod = np.prod([float(len(Bn)) for Bn in BN])
        result = 0.0 if not prod else mass_B/prod**(1.0/len(BN)) 
    elif option == 'susp':
        ratio = np.prod([float(len(Bn))/len(Rn) for Bn, Rn in zip(BN, RN)])
        result = -1.0 if not mass_B * ratio else mass_B * (np.log(mass_B/mass_R) - 1) + mass_R * ratio - mass_B * np.log(ratio)
    else: 
        raise Exception('wrong density measure input')
    return result
    
def select_dimension_by_cardinality(BN):
    return np.argmax([len(Bn) for Bn in BN])


def select_dimension_by_density(BN, RN, mass_BN, mass_B, mass_R, density_type):
    rho_tilda = -np.inf
    i_tilda = 0
    BN_prime = deepcopy(BN)
    
    for idx in range(len(BN)):
        BN_idx_list = BN[idx].keys()
        if len(BN_idx_list):
            mass_avg = mass_B / float(len(BN_idx_list))
            mass_i_array = np.array([mass_BN[idx][n] for n in BN_idx_list])
        
            D_idx = np.where(mass_i_array <= mass_avg)[0]
            Di = [BN_idx_list[i] for i in D_idx]
            
            total = 0
            for n in Di:
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
    start_time = time.time()
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
    parser.add_argument ('--density_type', dest='density_type', type=str, default='ari',
                         help="Density measure. Choose from 'ari', 'geo', and 'susp'. default 'ari'")
    parser.add_argument ('--selection_policy', dest='selection_policy', type=str, default='cardinality',
                         help="Dimension selection policy. Choose from 'cardinality' or 'density'. default 'cardinality'")
    parser.add_argument ('--verbose', dest='verbose', type=bool, default=False,
                         help="Print the selected k dense blocks. default 'Not print'")
    parser.add_argument ('--copy_table', dest='copy_table', type=bool, default=False,
                         help="Copy table mode in find_single_block. default False")
                         
    # create index
    parser.add_argument ('--indexing', dest='indexing', type=bool, default=False,
                         help="Whether or not to add indexing. default False")
    parser.add_argument ('--indexing_method', dest='indexing_method', type=str, default='btree',
                         help="Indexing method. default 'btree'")


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
        ts_sql_add_keep(db_conn, TS_TABLE)
        
        # create indexing
        if args.indexing:
            cur = db_conn.cursor()
            for da in dim_attr:
                cur.execute("CREATE INDEX %s" % (da + '_idx') +
                            " ON %s" % TS_TABLE + 
                            " USING %s" % args.indexing_method +
                            " (%s)" % da)
                db_conn.commit()
                print "Created index with method '%s' on %s" % (args.indexing_method, da)
        
        # run d-cube
        density_blocks, length_blocks = d_cube(db_conn, args.num_dense_blocks, dim_attr, measure_attr, args.density_type, args.selection_policy, args.copy_table)
        if args.verbose:
            cur = db_conn.cursor()
            for i in range(args.num_dense_blocks):
                print '#### result ####'
                cur.execute("SELECT * FROM %s" % (TS_RESULT + str(i)))
                print cur.fetchall()
        
        
        print '### RESULT ###'
        for i, density in enumerate(density_blocks):
            print 'dense block {:d} having {:d} tuples stored in {:s} with density {:f}'.format(i, length_blocks[i], TS_RESULT + str(i), density)

        ts_db_bubye(db_conn)
        
    except:
        print "Unexpected error:", sys.exc_info()[0]    
        if (db_conn):
            ts_db_bubye(db_conn)            
        raise                    

    print 'Elapsed time %f s' % (time.time() - start_time)

        
if __name__ == '__main__':
    main()
    
