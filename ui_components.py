import streamlit as st
import pandas as pd
from data_loader import ranking

def create_option_filters(prefix=""):
    filters = {'상향': {}, '적정': {}, '하향': {}}

    competition_enabled = st.checkbox("경쟁률 필터", key=f"{prefix}competition_filter")
    if competition_enabled:
        with st.expander("경쟁률 필터 설정"):
            for list_type in ['상향', '적정', '하향']:
                st.subheader(f"{list_type} 조건")
                col1, col2, col3 = st.columns([10, 1, 10])
                with col1:
                    filters[list_type]['2024년_경쟁률백분위'] = st.slider(f"경쟁률 백분위 (미만) ({list_type})", 0, 100,
                                                                 {'상향': 50, '적정': 50, '하향': 50}[list_type], 1,
                                                                 key=f"{prefix}competition_strength_{list_type}")
                with col2:
                    st.markdown("**|**")
                with col3:
                    filters[list_type]['2024년_경쟁률변동(%)'] = st.number_input(f"경쟁률 변동(%) (초과) ({list_type})",
                                                                           value={'상향': 0, '적정': -10, '하향': -20}[list_type], step=1,
                                                                           key=f"{prefix}competition_change_{list_type}")

    entry_score_enabled = st.checkbox("입결 필터", key=f"{prefix}entry_score_filter")
    if entry_score_enabled:
        with st.expander("입결 필터 설정"):
            for list_type in ['상향', '적정', '하향']:
                st.subheader(f"{list_type} 조건")
                col1, col2, col3 = st.columns([10, 1, 10])
                with col1:
                    filters[list_type]['2024년_입결70%변동(%)'] = st.number_input(f"입결70% 변동(%) (미만) ({list_type})",
                                                                             value={'상향': -10, '적정': 0, '하향': 10}[list_type], step=1,
                                                                             key=f"{prefix}entry_score_change_{list_type}")
                with col2:
                    st.markdown("**|**")
                with col3:
                    min_val, max_val = {'상향': (0.6, 0.8), '적정': (0.95, 1.1), '하향': (1.1, 1.3)}[list_type]
                    filters[list_type]['3개년_입결70%_평균'] = st.slider(f"3개년 입결70% 평균 (배수) ({list_type})",
                                                                   min_val, max_val,
                                                                   {'상향': 0.7, '적정': 1.0, '하향': 1.3}[list_type], 0.01,
                                                                   key=f"{prefix}entry_score_3year_{list_type}")

    fill_rate_enabled = st.checkbox("충원율 필터", key=f"{prefix}fill_rate_filter")
    if fill_rate_enabled:
        with st.expander("충원율 필터 설정"):
            for list_type in ['상향', '적정', '하향']:
                st.subheader(f"{list_type} 조건")
                col1, col2, col3 = st.columns([10, 1, 10])
                with col1:
                    filters[list_type]['2024년_충원율(%)'] = st.number_input(f"충원율(%) (초과) ({list_type})",
                                                                         value={'상향': 100, '적정': 50, '하향': 30}[list_type], step=1,
                                                                         key=f"{prefix}fill_rate_{list_type}")
                with col2:
                    st.markdown("**|**")
                with col3:
                    filters[list_type]['3개년_충원율_평균'] = st.number_input(f"3개년 충원율 평균(%) (초과) ({list_type})",
                                                                       value={'상향': 100, '적정': 50, '하향': 30}[list_type], step=1,
                                                                       key=f"{prefix}fill_rate_3year_{list_type}")

    return filters


def display_university_checklist(df, title, prefix=""):
    st.subheader(title)
    if df.empty:
        st.warning(f"{title}에 데이터가 없습니다.")
        return []

    if '대학명' not in df.columns:
        st.error(f"{title}의 데이터에 '대학명' 열이 없습니다.")
        return []

    ranking_dict = {univ: i for i, univ in enumerate(ranking)}
    universities = sorted(df['대학명'].unique(), key=lambda x: ranking_dict.get(x, float('inf')))
    selected_universities = []
    cols = st.columns(3)
    for i, univ in enumerate(universities):
        with cols[i % 3]:
            if st.checkbox(univ, key=f"{prefix}{title}_{univ}_{i}"):
                selected_universities.append(univ)
    return selected_universities


def display_university_data(df, title):
    st.subheader(title)
    if df.empty:
        st.warning(f"{title}에 데이터가 없습니다.")
        return pd.DataFrame()

    df['선택'] = False
    columns = ['선택'] + [col for col in df.columns if col != '선택']
    edited_df = st.data_editor(
        df[columns],
        hide_index=True,
        column_config={
            "선택": st.column_config.CheckboxColumn(
                "선택",
                default=False,
                help="이 행을 선택하려면 체크하세요"
            )
        },
        disabled=df.columns.drop('선택'),
        key=f"editor_{title.replace(' ', '_')}"
    )
    return edited_df[edited_df['선택']]