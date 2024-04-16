import pandas as pd
import pandss as pdss
import yaml


# Constants
monthfilter = [1,2,3,4,5,6,7,8,9,10,11,12]

month_map = {'Jan':1,'Feb':2,'Mar':3, 'Apr':4,
            'May':5,'Jun':6,'Jul':7, 'Aug':8,
            'Sep':9,'Oct':10,'Nov':11, 'Dec':12,}

month_list = ['Oct', 'Nov', 'Dec','Jan', 'Feb', 'Mar',
            'Apr', 'May', 'Jun','Jul', 'Aug', 'Sep']

wyt_map = {'Wet':1,'Above Normal':2,'Below Normal':3, 
           'Dry':4,'Critical':5}

wyt_list = ['Wet', 'Above Normal', 'Below Normal',
            'Dry', 'Critical']

def convert_cm_nums(monthchecklist)->list:
    '''
    Converts calendar month strings to calendar month numbers
    Jan=1, etc.
    '''
    monthfilter = []
    for v in monthchecklist:
        monthfilter.append(month_map[v])
    return monthfilter

def convert_wyt_nums(wytchecklist)->list:
    '''
    Converts WYT strings to numbers: Wet = 1, etc.
    '''
    wytfilter = []
    for v in wytchecklist:
        wytfilter.append(wyt_map[v])
    return wytfilter

def load_data_mult(scenarios, var_dict, date_map)->None:
    """
    # Load data from the selected DSS files into a .csv
    """
    print(date_map)
    dfi = pd.DataFrame()
    df = pd.DataFrame()
    appended_data = []

    for scenario in scenarios:
        print(scenario.pathname,scenario.alias)
        with pdss.DSS(scenario.pathname) as dss:
  
            # Loop to read all paths into DataFrame
            for var in var_dict:
                pn = var_dict[var]['pathname']
                path_i = pdss.DatasetPath.from_str(pn)
                print (pn)

                for regular_time_series in dss.read_multiple_rts(path_i):
                    dfi['Scenario'] = scenario.alias
                    dfi[regular_time_series.path.b] = regular_time_series.to_frame()
        
        # Make a list of the DataFrames associated with each DV file
        appended_data.append(dfi)
        dfi = pd.DataFrame()

    # concatenate the individual DataFrames into one big DataFrame
    df = pd.concat(appended_data)
    df = pd.merge(df,date_map, left_index=True, right_index=True)
    df.to_csv('temp.csv')
    #print(df)
    return

def make_ressum_df(scenlist,df:pd.DataFrame,var_dict,start_yr=1922,end_yr=2021,
                    monthfilter=monthfilter)->pd.DataFrame:
        df1 = df.loc[(df['icm'].isin(monthfilter)) &
                (df['iwy']>=start_yr) &(df['iwy']<=end_yr)
                ] 
        
        for i in df1:
            try:
                f = (var_dict[i]['table_display'])
                if f=='wy':
                    df1 = df1.drop(columns=i)
                    
            except KeyError:
                continue
        
        df_tbl = round(df1.groupby(["Scenario"]).sum()/(end_yr-start_yr+1))

        # Drop the index columns
        df_tbl.drop(['icy','icm','iwy','iwm','cfs_taf'],axis=1,inplace=True)

        df_tbl = df_tbl.T
        df_tbl['diff']=df_tbl[scenlist[1]]-df_tbl[scenlist[0]]
        df_tbl['perdiff'] = round((df_tbl[scenlist[1]]-df_tbl[scenlist[0]])/df_tbl[scenlist[0]],2)*100
        df_tbl.reset_index(inplace=True)
        return df_tbl

def cfs_taf(df:pd.DataFrame,var_dict:dict)->pd.DataFrame:
    for var in var_dict:
        b = var
        if var_dict[var]['table_convert']=='cfs_taf':
            #print(f'converted {b} to TAF')
            df[b]=df[b]*df['cfs_taf']
        else:
            continue
    return df

def make_summary_df(scenlist,df,var_dict,start_yr=1922,end_yr=2021,
                    monthfilter=monthfilter,bparts=None):


    df1 = df.loc[(df['icm'].isin(monthfilter)) &
                (df['iwy']>=start_yr) &(df['iwy']<=end_yr)
                ] 
    columns_to_drop = [col for col in df1.columns if 'S_' in col]
    df1 = df1.drop(columns=columns_to_drop)

    #print(var_dict)
    # Do Conversions
    for var in var_dict:
        if var_dict[var]['table_convert']=='cfs_taf':
            df1[var]=df1[var]*df1['cfs_taf']
        else:
            continue
    
    # Annual Average
    df_tbl = round(df1.groupby(["Scenario"]).sum()/(end_yr-start_yr+1))

    # Time slicing is done; drop the index columns
    df_tbl.drop(['icy','icm','iwy','iwm','cfs_taf'],axis=1,inplace=True)

    #df_tbl = df_tbl.reindex(df_tbl.index.values.tolist()+['BLANK'])
    #df_tbl["----"] = 0#pd.NA
    #print(df_tbl)
    # Filter B-Parts, if user-specified
    if bparts != None:
        df1 = df_tbl.loc[:,bparts]
        df_tbl = df1

    # Make a dictionary of just aliases to map to the dataframe
    alias_dict = {}
    type_dict = {}
    for key in var_dict:
        alias_dict[key]=var_dict[key]['alias']
        type_dict[key]=var_dict[key]['type']

    df_tbl = df_tbl.T
    df_tbl['description'] = df_tbl.index.map(alias_dict)
    df_tbl['type'] = df_tbl.index.map(type_dict)


    df_tbl['diff']=df_tbl[scenlist[1]].sub(df_tbl[scenlist[0]], fill_value = 0)
    df_tbl['perdiff'] = round(
            (df_tbl[scenlist[1]].sub(df_tbl[scenlist[0]], fill_value = 0))
            .div(df_tbl[scenlist[0]],fill_value = 0),
        2)*100

    #print(df_tbl)
    df_tbl.reset_index(inplace=True, names = "bpart")
    #df_tbl.loc[df_tbl.shape[0]] = None
    #df_tbl.loc[df_tbl.shape[0]-1,"bpart"]= "----"

    return df_tbl
    

def generate_yaml_file(varlist, filename):
    """
    Generate a YAML file with given data.

    Args:
    - data: Dictionary containing the data to be written to the YAML file.
    - filename: Name of the YAML file to be generated.
    """
    data = {}

    for var in varlist:
        data[var[0]] = {
            'bpart': var[0],
            'pathname': f'/CALSIM/{var[0]}/.*//.*/.*/',
            'alias': var[1],
            'table_convert': 'cfs_taf',
            'table_display': 'wy',
            'type': 'Channel'
        }    

    with open(filename, 'w') as file:
        yaml.dump(data, file)
    print(f"YAML file '{filename}' generated successfully.")

def read_csv_into_list(filename):
    data = []
    with open(filename, 'r', newline='') as file:
        reader = csv.reader(file,delimiter=',')
        for row in reader:
            data.append(row)
    return data

def remove_duplicates_from_yaml(filename):
    """
    Remove duplicate entries from a YAML file.

    Args:
    - filename: Name of the YAML file to process.
    """
    with open(filename, 'r') as file:
        data = yaml.safe_load(file)

    # Remove duplicates
    unique_data = remove_duplicates(data)

    # Write unique data back to the YAML file
    with open(filename, 'w') as file:
        yaml.dump(unique_data, file)

def remove_duplicates(data):
    """
    Remove duplicate entries with the same top-level keys from a nested dictionary.

    Args:
    - data: Nested dictionary to process.

    Returns:
    - Unique data (nested dictionary) without duplicates.
    """
    seen = {}
    unique_data = {}
    for key, value in data.items():
        if isinstance(value, dict):
            # Recursively process nested dictionaries
            unique_data[key] = remove_duplicates(value)
        elif key not in seen:
            # Add the first occurrence of the key
            seen[key] = value
            unique_data[key] = value
    return unique_data
