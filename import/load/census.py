from __future__ import with_statement
import os

from parse import census
from pprint import pprint, pformat

batch_mode = True
DATA_DIR='../data/'
tsv_file_format = DATA_DIR+'load/%s.tsv'


def load_census_meta(type):
    str_cols = set(['FILEID', 'STUSAB', 'CHARITER', 'CIFSN', 'LOGRECNO',])
    all_keys = {}
    # Build list
    for table in census.ALL_TABLES[type]:
        (_,_,pathMap) = census.parse_sas_file(type, table, all_keys)
    # Now insert
    for hr_key, int_keys in all_keys.items():
        for k in int_keys:
            if k in str_cols: continue
            db.insert('census_meta', 
                    seqname=False,
                    internal_key=k,
                    census_type=type,
                    hr_key=hr_key)


def load_census_data(type):
    geoTables = {}
    for row in census.parse_sum_files([type]): #,requesting_keys[type]):
        (layout, logrecno, fileid, stusab, chariter, cifsn, t, geo_file) = map(row.pop, 
                ['layout', 'LOGRECNO', 'FILEID', 'STUSAB', 'CHARITER', 'CIFSN', 'type', 'geo_file'])
        logrecno = int(logrecno)
        if geo_file not in geoTables:
            reqed_keys = set(['LOGRECNO','SUMLEV','STATE','CD110'])
            geoTables[geo_file] = dict([ (lrn, dict([(k,d[k]) for k in filter(lambda x: x in reqed_keys, d.keys())])) for lrn,d in census.build_geo_table(geo_file).items()])
        geo = geoTables[geo_file]
        if logrecno in geo:
            ### Entries for states
            loc_code = ''
            if geo[logrecno]['SUMLEV'] == 'STATE':
                loc_code = geo[logrecno]['STATE']
            ### Entries for the 110th Congress.
            elif geo[logrecno]['SUMLEV'] == 'DISTS' \
                    and geo[logrecno]['CD110']:
                loc_code = '%s-%02d' % (geo[logrecno]['STATE'], int(geo[logrecno]['CD110']))
            else: continue

            for internal_key, value in row.items():
                db.insert('census_data', seqname=False, location=loc_code, internal_key=internal_key, census_type=type, value=value)

def main():
    for type in [1, 3]:
        load_census_meta(type)
        load_census_data(type)

if __name__ == "__main__":
    if batch_mode:
        from bulk_loader import bulk_loader_db
        db = bulk_loader_db(os.environ.get('WATCHDOG_TABLE', 'watchdog_dev'))
        meta_cols = ['internal_key', 'census_type', 'hr_key']
        db.open_table('census_meta', meta_cols, filename=tsv_file_format%'census_meta')
        data_cols = ['location', 'internal_key', 'census_type', 'value']
        db.open_table('census_data', data_cols, filename=tsv_file_format%'census_data')
        main()
    else:
        from tools import db
        with db.transaction():
            #db.delete('census_data', where='1=1')
            #db.delete('census_meta', where='1=1')
            main()

