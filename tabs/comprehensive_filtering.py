import streamlit as st
import pandas as pd
from data_loader import data, ranking, remove_duplicates
from filters import filter_data_comprehensive
from category_mapping import DETAIL_TO_MID_CATEGORY, MID_TO_MAIN_CATEGORY

def create_filter_box(title, content):
    st.markdown(f"""
    <style>
    .filter-box {{
        background-color: #f0f2f6;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
    }}
    .filter-title {{
        font-weight: bold;
        margin-bottom: 5px;
        color: #262730;
    }}
    </style>
    <div class="filter-box">
        <div class="filter-title">{title}</div>
        {content}
    </div>
    """, unsafe_allow_html=True)


def add_search_range_selector(prefix):
    search_range = st.radio(
        "대계열은 '인문'/ 중계열은 '상경계열'/ 소계열은 '경영'을 뜻합니다.",
        ("대계열 검색", "중계열 검색", "소계열 검색"),
        horizontal=True,
        key=f"{prefix}_search_range"
    )
    return search_range


def filter_by_search_range(df, student_info, search_range):
    if df.empty:
        return df

    if search_range == "대계열 검색":
        return df[df['계열'].isin(student_info['field'])]
    elif search_range == "중계열 검색":
        mid_categories = list(set([DETAIL_TO_MID_CATEGORY.get(field, "") for field in student_info['detail_fields']]))
        return df[df['계열구분'].isin(mid_categories)]
    elif search_range == "소계열 검색":
        return df[df['계열상세명'].apply(
            lambda x: any(field.lower() in str(x).lower() for field in student_info['detail_fields']))]
    return df


def sort_by_ranking(df):
    ranking_dict = {univ: i for i, univ in enumerate(ranking)}
    df['ranking'] = df['대학명'].map(ranking_dict)
    df = df.sort_values('ranking')
    df = df.drop('ranking', axis=1)
    return df


def display_ranked_university_checklist(df, title, prefix=""):
    st.subheader(title)
    if df.empty:
        st.warning(f"{title}에 데이터가 없습니다.")
        return []

    if '대학명' not in df.columns:
        st.error(f"{title}의 데이터에 '대학명' 열이 없습니다.")
        return []

    ranking_dict = {univ: i for i, univ in enumerate(ranking)}
    sorted_universities = sorted(df['대학명'].unique(), key=lambda x: ranking_dict.get(x, len(ranking)))


    selected_universities = []
    cols = st.columns(3)
    for i, univ in enumerate(sorted_universities):
        with cols[i % 3]:
            if st.checkbox(univ, key=f"{prefix}{title}_{univ}_{i}"):
                selected_universities.append(univ)
    return selected_universities

@st.cache_data
def apply_second_filtering(df, selected_universities):
    filtered_df = df[df['대학명'].isin(selected_universities)]
    filtered_df = remove_duplicates(filtered_df)
    filtered_df = sort_by_ranking(filtered_df)
    return reorder_columns(filtered_df)


def create_advanced_filters(prefix):
    filters = {}

    if st.checkbox("모집인원 필터 적용", key=f"{prefix}_recruitment_filter"):
        with st.expander("모집인원 필터 설정"):
            min_recruitment = st.number_input("최소 모집인원", min_value=1, value=5, step=1,
                                              key=f"{prefix}_min_recruitment")
            filters['2025년_모집인원'] = min_recruitment

    if st.checkbox("경쟁률 필터 적용", key=f"{prefix}_competition_filter"):
        with st.expander("경쟁률 필터 설정"):
            # 작년 경쟁률 필터를 수치 입력으로 변경
            low_competition = st.number_input("작년 경쟁률(이하)", min_value=0.0, value=10.0, step=0.1,
                                              key=f"{prefix}_low_competition")
            if low_competition < 100:  # 100 이상의 값은 무시 (실질적으로 필터링하지 않음)
                filters['2024년_경쟁률'] = low_competition

            col1, col2 = st.columns(2)
            with col1:
                competition_percentile = st.slider("작년 경쟁률 백분위", 0, 100, (10, 70), 1,
                                                   key=f"{prefix}_competition_percentile")
                filters['2024년_경쟁률백분위'] = competition_percentile

            with col2:
                competition_avg_percentile = st.slider("3개년 평균 경쟁률 백분위", 0, 100, (0, 80), 1,
                                                       key=f"{prefix}_competition_avg_percentile")
                filters['3개년_경쟁률_평균'] = competition_avg_percentile

            st.write("\n")
            st.write("경쟁률 변동 정도 (%)")
            col3, col4 = st.columns(2)
            with col3:
                competition_change_min = st.number_input("최소(-100)", -100, 0, 0,
                                                         key=f"{prefix}_competition_change_min")
            with col4:
                competition_change_max = st.number_input("최대(1000)", 1, 1000, 300,
                                                         key=f"{prefix}_competition_change_max")
            filters['2024년_경쟁률변동(%)'] = (competition_change_min, competition_change_max)

    if st.checkbox("입결 필터 적용", key="comprehensive_entry_score_filter"):
        with st.expander("입결 필터 설정"):
            col1, col2 = st.columns(2)
            with col1:
                entry_score_percentile = st.slider("작년 입결 백분위", 0, 100, (30, 70), 1, key="comprehensive_entry_score_percentile")
                filters['2024년_입결70%'] = entry_score_percentile

            st.write("작년 입결70% 변동 정도 (%)")
            col3, col4 = st.columns(2)
            with col3:
                entry_score_change_min = st.number_input("최소(-100)", -100, -1, -100, key="comprehensive_entry_score_change_min")
            with col4:
                entry_score_change_max = st.number_input("최대(200)", 0, 200, 0, key="comprehensive_entry_score_change_max")
            filters['2024년_입결70%변동(%)'] = (entry_score_change_min, entry_score_change_max)

    if st.checkbox("충원율 필터 적용", key="comprehensive_fill_rate_filter"):
        with st.expander("충원율 필터 설정"):
            col1, col2 = st.columns(2)
            with col1:
                fill_rate = st.slider("작년 충원율", 0, 500, (100, 300), 1, key="comprehensive_fill_rate")
                filters['2024년_충원율(%)'] = fill_rate

            with col2:
                fill_rate_avg = st.slider("3개년 충원율", 0, 500, (80, 300), 1, key="comprehensive_fill_rate_avg")
                filters['3개년_충원율_평균'] = fill_rate_avg

    return filters

def apply_advanced_filters(df, filters):
    for key, value in filters.items():
        if key == '2024년_경쟁률':
            df = df[df[key] <= value]
        elif isinstance(value, tuple):  # 범위 필터
            df = df[(df[key] >= value[0]) & (df[key] <= value[1])]
        elif key in ['2024년_경쟁률백분위', '3개년_경쟁률_평균', '2024년_입결70%', '2024년_입결50%']:
            df = df[(df[key] >= value[0]) & (df[key] <= value[1])]
        else:  # 단일 값 필터
            df = df[df[key] >= value]
    return df


def reorder_columns(df):
    first_columns = ['선택', '대학명', '모집단위', '2024년_입결50%', '2024년_입결70%', '2024년_경쟁률', '전형명', '2025년_모집인원', '2024년_충원율(%)', '2025년_최저요약']
    other_columns = [col for col in df.columns if col not in first_columns + ['No.', '계열상세']]

    # '선택' 컬럼이 없는 경우 추가
    if '선택' not in df.columns:
        df['선택'] = True

    return df[first_columns + other_columns]

def show_comprehensive_filtering():
    if 'student_info' not in st.session_state:
        st.warning("정보입력 탭에서 먼저 정보를 입력하세요.")
        return

    student_info = st.session_state['student_info']

    st.info("학종 전형 필터링을 위한 조건을 설정해보세요.")

    create_filter_box("🔍 검색 범위", "")
    search_range = add_search_range_selector("comprehensive")

    create_filter_box("⚙️ 옵션 필터", "")
    filters = create_advanced_filters(prefix="comprehensive")

    create_filter_box("📊 수능최저역량", "")
    lowest_ability_filter = st.checkbox("수능최저역량 반영", key="comprehensive_lowest_ability")
    st.session_state['student_info']['lowest_ability_filter'] = lowest_ability_filter

    st.markdown("&nbsp;")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("1차 필터링", key="comprehensive_first_filter_button"):
            filtered_data = filter_data_comprehensive(student_info, data)

            if isinstance(filtered_data, pd.DataFrame) and not filtered_data.empty:
                filtered_data = filter_by_search_range(filtered_data, student_info, search_range)
                filtered_data = apply_advanced_filters(filtered_data, filters)

                if lowest_ability_filter:
                    filtered_data = filtered_data[filtered_data['2025년_수능최저코드'] <= student_info['lowest_ability_code']]

                # 데이터 분류
                general_data = filtered_data[filtered_data['분류'] == '일반']
                new_advanced_data = filtered_data[filtered_data['분류'].isin(['신설', '첨단'])]

                general_data = sort_by_ranking(general_data)
                new_advanced_data = sort_by_ranking(new_advanced_data)

                st.session_state['comprehensive_first_filter_results'] = general_data
                st.session_state['comprehensive_new_or_advanced'] = new_advanced_data
                st.success("1차 필터링이 완료되었습니다.")
            else:
                st.warning("필터링 결과가 없습니다.")
                st.session_state['comprehensive_first_filter_results'] = pd.DataFrame()
                st.session_state['comprehensive_new_or_advanced'] = pd.DataFrame()

    if 'comprehensive_first_filter_results' in st.session_state:
        st.markdown("---")
        st.markdown("&nbsp;")
        st.subheader("1️⃣ 1차 필터링 결과")
        df = st.session_state['comprehensive_first_filter_results']
        if isinstance(df, pd.DataFrame):
            if not df.empty and '대학명' in df.columns:
                df = reorder_columns(df)  # 컬럼 재정렬
                selected = display_ranked_university_checklist(df, "필터링된 대학 리스트", prefix="comprehensive_")
                st.session_state['comprehensive_selected_universities'] = selected
            else:
                st.warning("필터링된 데이터가 없거나 '대학명' 열이 없습니다.")
        else:
            st.warning("필터링 결과가 DataFrame 형식이 아닙니다.")

    with col2:
        if st.button("2차 필터링", key="comprehensive_second_filter_button"):
            general_df = st.session_state.get('comprehensive_first_filter_results', pd.DataFrame())
            new_advanced_df = st.session_state.get('comprehensive_new_or_advanced', pd.DataFrame())

            if isinstance(general_df, pd.DataFrame) and isinstance(new_advanced_df, pd.DataFrame):
                selected = st.session_state.get('comprehensive_selected_universities', [])

                if not general_df.empty and '대학명' in general_df.columns:
                    filtered_general_df = apply_second_filtering(general_df, selected)
                    st.session_state['comprehensive_second_filter_results'] = filtered_general_df

                if not new_advanced_df.empty and '대학명' in new_advanced_df.columns:
                    filtered_new_advanced_df = apply_second_filtering(new_advanced_df, selected)
                    st.session_state['comprehensive_new_or_advanced_filtered'] = filtered_new_advanced_df

                st.success("2차 필터링이 완료되었습니다.")
            else:
                st.warning("필터링 결과가 DataFrame 형식이 아닙니다.")

    if 'comprehensive_second_filter_results' in st.session_state:
        st.markdown("---")
        st.markdown("&nbsp;")
        st.subheader("2️⃣ 2차 필터링 결과")
        df = st.session_state['comprehensive_second_filter_results']
        if isinstance(df, pd.DataFrame) and not df.empty:
            st.write("**필터링된 대학 리스트**")
            for univ in df['대학명'].unique():
                st.write(f"**{univ}**")
                group = df[df['대학명'] == univ]
                edited_df = st.data_editor(
                    group,
                    hide_index=True,
                    column_config={
                        "선택": st.column_config.CheckboxColumn(
                            "선택",
                            help="이 행을 선택하려면 체크하세요"
                        )
                    },
                    disabled=group.columns.drop('선택'),
                    key=f"editor_comprehensive_{univ}"
                )
                st.session_state[f'comprehensive_displayed_{univ}'] = edited_df
        else:
            st.warning("필터링된 리스트에 데이터가 없습니다.")

        # 신설 및 첨단융합 학과 표시
        st.subheader("신설 또는 첨단융합 학과")
        new_df = st.session_state.get('comprehensive_new_or_advanced_filtered', pd.DataFrame())
        if not new_df.empty:
            edited_new_df = st.data_editor(
                new_df,
                hide_index=True,
                column_config={
                    "선택": st.column_config.CheckboxColumn(
                        "선택",
                        help="이 행을 선택하려면 체크하세요"
                    )
                },
                disabled=new_df.columns.drop('선택'),
                key="editor_comprehensive_new_or_advanced"
            )
            st.session_state['comprehensive_new_or_advanced_edited'] = edited_new_df
        else:
            st.write("선택된 대학의 신설 또는 첨단융합 학과가 없습니다.")



    with col3:
        if st.button("결과 저장", key="save_comprehensive_results_button"):
            saved_results = pd.DataFrame()
            df = st.session_state.get('comprehensive_second_filter_results', pd.DataFrame())
            new_df = st.session_state.get('comprehensive_new_or_advanced_edited', pd.DataFrame())

            if isinstance(df, pd.DataFrame):
                if not df.empty and '대학명' in df.columns:
                    for univ in df['대학명'].unique():
                        if f'comprehensive_displayed_{univ}' in st.session_state:
                            univ_df = st.session_state[f'comprehensive_displayed_{univ}']
                            saved_results = pd.concat([saved_results, univ_df[univ_df['선택']]])

            if isinstance(new_df, pd.DataFrame) and not new_df.empty:
                saved_results = pd.concat([saved_results, new_df[new_df['선택']]])

            saved_results = reorder_columns(saved_results)
            saved_results = sort_by_ranking(saved_results)
            st.session_state['saved_comprehensive_results'] = saved_results
            total_count = len(saved_results)
            st.success(f"결과가 저장되었습니다. 총 {total_count}개의 학과가 저장되었습니다.")


if __name__ == "__main__":
    show_comprehensive_filtering()
