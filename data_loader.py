### data_loader.py ###
# data_loader.py
import streamlit as st
import pandas as pd
import json

@st.cache_data
def load_data(file_path):
    return pd.read_excel(file_path)

def load_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

data = load_data('data_240806_1610.xlsx')
additional_data = load_data('uni_info_summary_240802.xlsx')
lowest_ability_data = load_json('lowest_ability_codes.json')
lowest_ability_codes = lowest_ability_data['codes']
lowest_ability_ui_options = lowest_ability_data['ui_options']

def load_expert_knowledge(file_path='expert_knowledge.txt'):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

expert_knowledge = load_expert_knowledge()


import json

def load_university_ranges(file_path='university_ranges.json'):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

university_ranges = load_university_ranges()

SCHOOL_TYPE_ADJUSTMENT = {
    "일반고": 1.0,
    "학군지 일반고": 0.9,
    "지역자사고": 0.9,
    "전사고": 0.7,
    "과학고": 0.7,
    "외고": 0.8
}

university_groups = {
    "그룹1": ["서울대학교", "연세대학교", "고려대학교"],
    "그룹2": ["서강대학교", "성균관대학교", "한양대학교"],
    "그룹3": ["중앙대학교", "경희대학교", "한국외국어대학교", "서울시립대학교", "이화여자대학교"],
    "그룹4": ["건국대학교", "동국대학교", "홍익대학교"],
    "그룹5": ["숙명여자대학교", "국민대학교", "서울과학기술대학교", "숭실대학교", "세종대학교"],
    "그룹6": ["부산대학교", "경북대학교", "인하대학교", "아주대학교"],
    "그룹7": ["광운대학교", "명지대학교", "상명대학교", "단국대학교", "한국항공대학교"],
    "그룹8": ["전남대학교", "충남대학교", "성신여자대학교", "가천대학교", "한양대학교(에리카)"],
    "그룹9": ["한성대학교", "서경대학교", "삼육대학교", "동덕여자대학교", "덕성여자대학교", "서울여자대학교"],
    "그룹10": ["인천대학교", "가톨릭대학교", "경기대학교"],
    "그룹11": ["충북대학교", "전북대학교", "강원대학교", "부경대학교", "제주대학교"],
    "그룹12": ["연세대학교(미래)", "고려대학교(세종)", "단국대학교(천안)"],
    "그룹13": []  # 위 그룹에 포함되지 않은 대학들을 위한 그룹
}

# 주어진 대학 목록에서 그룹에 포함되지 않은 대학들을 "그룹13"에 추가
all_universities = set(university_ranges.keys())
grouped_universities = set(univ for group in university_groups.values() for univ in group)
university_groups["그룹13"] = list(all_universities - grouped_universities)

# 각 대학이 어떤 그룹에 속하는지 빠르게 찾기 위한 딕셔너리
university_to_group = {}
for group_name, universities in university_groups.items():
    for univ in universities:
        university_to_group[univ] = group_name

def get_university_group(university):
    return university_to_group.get(university, "그룹13")

def get_group_universities(group):
    return university_groups.get(group, [])


ranking = [
    "서울대학교",
    "연세대학교",
    "고려대학교",
    "서강대학교",
    "성균관대학교",
    "한양대학교",
    "중앙대학교",
    "경희대학교",
    "이화여자대학교",
    "서울시립대학교",
    "한국외국어대학교",
    "건국대학교",
    "동국대학교",
    "홍익대학교",
    "숙명여자대학교",
    "숭실대학교",
    "국민대학교",
    "아주대학교",
    "서울과학기술대학교",
    "세종대학교",
    "인하대학교",
    "단국대학교",
    "성신여자대학교",
    "한국항공대학교",
    "한양대학교(에리카)",
    "광운대학교",
    "가천대학교",
    "명지대학교",
    "상명대학교",
    "서울여자대학교",
    "가톨릭대학교",
    "한국외국어대학교(글로벌)",
    "덕성여자대학교",
    "동덕여자대학교",
    "경기대학교",
    "인천대학교",
    "한성대학교",
    "삼육대학교",
    "서경대학교"
]
