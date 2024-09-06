from pathlib import Path

from pandas import DataFrame, read_json, concat


def _basic(_df_voc):
    with (Path(__file__).parent / 'support_voc.json').open('r', encoding='utf-8', errors='ignore') as f:
        _par = read_json(f)

    # parameter
    _keys = _df_voc.keys()

    invalid_keys = [key for key in _df_voc.keys() if key not in set(_par.keys())]

    if invalid_keys:
        raise KeyError(f'\n\t\t{invalid_keys} are not supported keys.'
                       f'\n\t\tPlease check the\033[91m support_voc.md\033[0m file to use the correct name.')

    _MW, _MIR, _SOAP, _KOH = _par.loc['MW', :], _par.loc['MIR', :], _par.loc['SOAP', :], _par.loc['KOH', :]

    _voc_classify = {
        'alkane_total': ['Ethane', 'Propane', 'Isobutane', 'n-Butane', 'Isopentane', 'n-Pentane', 'n-Hexane',
                         'n-Heptane', 'n-Octane', 'n-Nonane', 'n-Decane', 'n-Undecane', 'n-Dodecane',

                         'Cyclopentane', 'Methylcyclopentane', 'Cyclohexane', 'Methylcyclohexane',

                         '2,2-Dimethylbutane', '2,3-Dimethylbutane', '2-Methylpentane', '3-Methylpentane',
                         '2,4-Dimethylpentane', '2-Methylhexane', '3-Methylhexane',
                         '2,2,4-Trimethylpentane', '2,3,4-Trimethylpentane', '2-Methylheptane', '3-Methylheptane'],

        'alkene_total': ['Ethylene', 'Propylene', '1-Butene', 't-2-Butene', 'cis-2-Butene', '1-Pentene', 't-2-Pentene',
                         'cis-2-Pentene', '1-Hexene', 'Isoprene', '1.3-Butadiene', '1-Octene'],

        'aromatic_total': ['Benzene', 'Toluene', 'Ethylbenzene', 'm/p-Xylene', 'o-Xylene', 'Styrene',
                           'Isopropylbenzene',
                           'n-Propylbenzene', 'm-Ethyltoluene', 'p-Ethyltoluene', 'o-Ethyltoluene', 'm-Diethylbenzene',
                           'p-Diethylbenzene', '1,2,4-Trimethylbenzene', '1,2,3-Trimethylbenzene',
                           '1,3,5-Trimethylbenzene', ],

        'alkyne_total': ['Acetylene'],

        'OVOC': ['Acetaldehyde', 'Ethanol', 'Acetone', 'IPA', 'Ethyl Acetate', 'Butyl Acetate'],

        'ClVOC': ['VCM', 'TCE', 'PCE', '1.4-DCB', '1.2-DCB'],
    }

    _df_MW = (_df_voc * _MW).copy()
    _df_dic = {
        'Conc': _df_voc.copy(),
        'OFP': _df_MW / 48 * _MIR,
        'SOAP': _df_MW / 24.5 * _SOAP / 100 * 0.054,
        'LOH': _df_MW / 24.5 / _MW * 0.602 * _KOH,
    }

    # calculate
    _out = {}
    for _nam, _df in _df_dic.items():

        _df_out = DataFrame(index=_df_voc.index)

        for _voc_nam, _voc_lst in _voc_classify.items():
            _lst = list(set(_keys) & set(_voc_lst))
            if len(_lst) == 0:
                continue

            _df_out = concat([_df[_lst], _df_out], axis=1)

            _df_out[_voc_nam] = _df[_lst].sum(axis=1, min_count=1)

        _df_out['Total'] = _df.sum(axis=1, min_count=1)

        _out[_nam] = _df_out

    return _out


def markdown_table_to_dataframe():
    import pandas as pd
    from pathlib import Path

    # support_voc.md
    with open(Path(__file__).parent / 'support_voc.md', 'r', encoding='utf-8') as file:
        markdown_content = file.read()

    # 將內容分割成行
    lines = markdown_content.strip().split('\n')

    # 提取表頭
    headers = [col.strip() for col in lines[0].split('|')[1:-1]]

    # 解析數據行
    data = []
    for line in lines[2:]:  # 跳過表頭和分隔行
        columns = [col.strip() for col in line.split('|')[1:-1]]
        data.append(columns)

    # 創建 DataFrame
    df = pd.DataFrame(data, columns=headers)

    # 轉換數據類型
    numeric_columns = ['MIR', 'MW', 'SOAP', 'KOH']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.set_index('Species').T

    df = df.iloc[:, :-7]

    df.to_json(Path(__file__).parent / 'support_voc.json', indent=4)
