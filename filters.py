import pandas as pd
from data_loader import SCHOOL_TYPE_ADJUSTMENT, university_ranges, ranking


def get_substitute_column_name(column):
    substitutions = {
        '2024년_경쟁률': '2024년_계열경쟁률',
        '2024년_경쟁률백분위': '2024년_계열경쟁률백분위',
        '2024년_경쟁률변동(%)': '2024년_계열경쟁률변동(%)',
        '3개년_경쟁률_평균': '3개년_계열경쟁률_평균',
        '2024년_입결70%': '2024년_계열입결70%',
        '2024년_입결70%변동(%)': '2024년_계열입결70%변동(%)',
        '3개년_입결70%_평균': '3개년_계열입결70%_평균',
        '2024년_충원율(%)': '2024년_계열충원율(%)',
        '3개년_충원율_평균': '3개년_계열충원율_평균'
    }
    return substitutions.get(column, column)

def get_column_value(df, row, column):
    if row['대체데이터사용'] == 1:
        substitute_column = get_substitute_column_name(column)
        return df.loc[(df['대학명'] == row['대학명']) & (df['전형구분'] == row['전형구분']), substitute_column].iloc[0]
    return row[column]


def apply_filters(df, filters, student_info):
    if not filters:
        return df

    for key, value in filters.items():
        mask = pd.Series(True, index=df.index)
        for idx, row in df.iterrows():
            column_value = get_column_value(df, row, key)
            if key == '2024년_경쟁률':
                mask.loc[idx] = column_value <= value
            elif '경쟁률백분위' in key or '입결70%변동(%)' in key:
                mask.loc[idx] = column_value < value
            elif '경쟁률변동(%)' in key or '충원율(%)' in key or '3개년_충원율_평균' in key:
                mask.loc[idx] = column_value > value
            elif '3개년_입결70%_평균' in key:
                mask.loc[idx] = column_value > student_info['adjusted_score'] * value
        df = df[mask]
    return df


def get_entry_score(row, filtered_data):
    entry_score_70 = row['2024년_입결70%']
    entry_score_50 = row['2024년_입결50%']

    if pd.notna(entry_score_70) and entry_score_70 not in [0, -9999]:
        return entry_score_70
    elif pd.notna(entry_score_50) and entry_score_50 not in [0, -9999]:
        return entry_score_50
    else:
        return get_column_value(filtered_data, row, '2024년_입결70%')


def filter_data(student_info, data):
    school_type = student_info['school_type']
    adjustment_factor = SCHOOL_TYPE_ADJUSTMENT.get(school_type, 1.0)
    adjusted_score = max(student_info['score'] * adjustment_factor, 1.00)

    filtered_data = data[data['대학명'].isin([
        univ for univ, range_info in university_ranges.items()
        if range_info['min'] <= adjusted_score <= range_info['max']
    ])]

    filtered_data = filtered_data[filtered_data['2025년_모집인원'] > 0]

    if '교과' in student_info['admission_type']:
        filtered_data = filtered_data[filtered_data['전형구분'] == '교과']
    else:
        return pd.DataFrame()

    if student_info['gender'] == '남자':
        filtered_data = filtered_data[~filtered_data['대학명'].str.contains('여자')]

    if student_info['school_type'] == '과학고':
        filtered_data = filtered_data[filtered_data['과학고'] == 1]
    elif student_info['school_type'] == '전사고':
        filtered_data = filtered_data[filtered_data['전사고'] == 1]
    elif student_info['school_type'] == '외고':
        filtered_data = filtered_data[filtered_data['외고'] == 1]

    return filtered_data


def filter_data_comprehensive(student_info, data):
    school_type = student_info['school_type']
    adjustment_factor = SCHOOL_TYPE_ADJUSTMENT.get(school_type, 1.0)
    adjusted_score = max(student_info['score'] * adjustment_factor, 1.00)

    filtered_data = data[data['대학명'].isin([
        univ for univ, range_info in university_ranges.items()
        if range_info['min'] <= adjusted_score <= range_info['max']
    ])]

    filtered_data = filtered_data[filtered_data['계열'].isin(student_info['field'])]
    filtered_data = filtered_data[filtered_data['전형구분'] == '종합']
    filtered_data = filtered_data[filtered_data['2025년_모집인원'] > 0]

    if student_info['gender'] == '남자':
        filtered_data = filtered_data[~filtered_data['대학명'].str.contains('여자')]

    if student_info['school_type'] == '과학고':
        filtered_data = filtered_data[filtered_data['과학고'] == 1]
    elif student_info['school_type'] == '전사고':
        filtered_data = filtered_data[filtered_data['전사고'] == 1]
    elif student_info['school_type'] == '외고':
        filtered_data = filtered_data[filtered_data['외고'] == 1]

    return filtered_data
