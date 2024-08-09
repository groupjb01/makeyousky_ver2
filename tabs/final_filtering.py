import streamlit as st
import pandas as pd
from data_loader import ranking

def sort_universities(df, sort_option, sort_order):
    ascending = (sort_order == '오름차순')
    if sort_option == '경쟁률 백분위':
        return df.sort_values('2024년_경쟁률백분위', ascending=ascending)
    elif sort_option == '경쟁률':
        return df.sort_values('2024년_경쟁률', ascending=ascending)
    elif sort_option == '3개년 경쟁률 백분위 평균':
        return df.sort_values('3개년_경쟁률_평균', ascending=ascending)
    elif sort_option == '입결70% 변동(%)':
        return df.sort_values('2024년_입결70%변동(%)', ascending=ascending)
    elif sort_option == '3개년 입결70% 평균':
        return df.sort_values('3개년_입결70%_평균', ascending=ascending)
    elif sort_option == '충원율(%)':
        return df.sort_values('2024년_충원율(%)', ascending=ascending)
    elif sort_option == '3개년 충원율 평균':
        return df.sort_values('3개년_충원율_평균', ascending=ascending)
    elif sort_option == '수능최저':
        return df.sort_values('2025년_수능최저코드', ascending=ascending)
    elif sort_option == '입결70%':
        return df.sort_values('2024년_입결70%', ascending=ascending)
    elif sort_option == '입결50%':
        return df.sort_values('2024년_입결50%', ascending=ascending)
    else:
        return df

def order_by_ranking(df):
    if '대학명' not in df.columns:
        st.warning("데이터프레임에 '대학명' 열이 없습니다.")
        return df

    df['ranking'] = df['대학명'].apply(lambda x: ranking.index(x) if x in ranking else len(ranking))
    return df.sort_values('ranking').drop('ranking', axis=1)

def reorder_columns(df):
    first_columns = ['선택', '대학명', '모집단위', '2024년_입결50%', '2024년_입결70%', '2024년_경쟁률', '전형명', '2025년_모집인원', '2024년_충원율(%)', '2025년_최저요약']
    excluded_columns = ['No.', '계열상세']
    other_columns = [col for col in df.columns if col not in first_columns + excluded_columns]
    return df[first_columns + other_columns]

@st.cache_data
def apply_final_filtering(general_data, sort_option, sort_order):
    if not general_data.empty:
        # 대학 랭킹에 따라 정렬
        ranking_dict = {univ: i for i, univ in enumerate(ranking)}
        general_data['temp_ranking'] = general_data['대학명'].map(ranking_dict).fillna(len(ranking))
        general_data = general_data.sort_values('temp_ranking')

        # 각 대학 내에서 정렬 기준 적용
        sorted_general = general_data.groupby('대학명', group_keys=False).apply(
            lambda x: sort_universities(x, sort_option, sort_order)
        )

        sorted_general['선택'] = False
        sorted_general['구분'] = '일반'
        sorted_general = reorder_columns(sorted_general)
        return sorted_general.drop('temp_ranking', axis=1)
    return pd.DataFrame()


@st.cache_data
def prepare_new_advanced_data(new_advanced_data):
    if not new_advanced_data.empty:
        sorted_new_advanced = order_by_ranking(new_advanced_data)
        sorted_new_advanced['선택'] = True
        sorted_new_advanced['구분'] = '신설/첨단'
        sorted_new_advanced = reorder_columns(sorted_new_advanced)
        return sorted_new_advanced
    return pd.DataFrame()


def show_final_filtering():
    st.info("교과, 학종 필터링 결과를 조건에 따라 정렬하여 리스트별 최대 20개의 대학을 선정합니다.")

    if 'subject_second_filter_results' not in st.session_state or 'comprehensive_second_filter_results' not in st.session_state:
        st.warning("교과 필터링과 학종 필터링을 먼저 완료해주세요.")
        return

    subject_general = st.session_state['subject_second_filter_results']
    subject_new_advanced = st.session_state['subject_new_or_advanced_filtered']
    comprehensive_general = st.session_state['comprehensive_second_filter_results']
    comprehensive_new_advanced = st.session_state['comprehensive_new_or_advanced_filtered']

    if st.button("전형별 저장 데이터 보기"):
        st.markdown("---")
        st.markdown("&nbsp;")
        st.subheader("1️⃣  전형별 저장 데이터 보기")

        st.subheader("📚 교과 지원 리스트")
        if not subject_general.empty:
            st.write("일반 학과")
            st.dataframe(reorder_columns(subject_general))
        if not subject_new_advanced.empty:
            st.write("신설/첨단 학과")
            st.dataframe(reorder_columns(subject_new_advanced))

        st.markdown("<hr style='border-top: 3px dashed #bbb;'>", unsafe_allow_html=True)

        st.subheader("📋 학종 지원 리스트")
        if not comprehensive_general.empty:
            st.write("일반 학과")
            st.dataframe(reorder_columns(comprehensive_general))
        if not comprehensive_new_advanced.empty:
            st.write("신설/첨단 학과")
            st.dataframe(reorder_columns(comprehensive_new_advanced))

    admission_types = ['교과', '학종']
    sort_options = [
        '입결70%',
        '입결50%',
        '경쟁률',
        '경쟁률 백분위',
        '경쟁률 변동(%)',
        '3개년 경쟁률 백분위 평균',
        '입결70% 변동(%)',
        '3개년 입결70% 평균',
        '충원율(%)',
        '3개년 충원율 평균',
        '수능최저'
    ]

    st.markdown("---")
    st.markdown("&nbsp;")
    st.subheader("2️⃣  정렬 조건 설정")

    with st.form(key='sorting_form'):
        for admission_type in admission_types:
            emoji = "📚" if admission_type == "교과" else "📋"
            st.subheader(f"{emoji} {admission_type} 전형")
            sort_option = st.selectbox(
                "정렬 기준",
                sort_options,
                key=f'{admission_type}_sort'
            )
            sort_order = st.selectbox(
                "정렬 순서",
                ["내림차순", "오름차순"],
                key=f'{admission_type}_order'
            )
            st.markdown("&nbsp;")

        submit_button = st.form_submit_button(label="최종 필터링 적용")

    if submit_button:
        final_results = {}

        for admission_type in admission_types:
            if admission_type == '교과':
                general_data = subject_general
                new_advanced_data = subject_new_advanced
            else:
                general_data = comprehensive_general
                new_advanced_data = comprehensive_new_advanced

            sort_option = st.session_state[f'{admission_type}_sort']
            sort_order = st.session_state[f'{admission_type}_order']

            final_results[admission_type] = apply_final_filtering(general_data, sort_option, sort_order)
            final_results[f'{admission_type}_신설첨단'] = prepare_new_advanced_data(new_advanced_data)

        st.session_state['final_results'] = final_results
        st.success("최종 필터링이 적용되었습니다.")

    if 'final_results' in st.session_state:
        st.subheader("최종 필터링 결과")
        for i, (key, df) in enumerate(st.session_state['final_results'].items()):
            if '신설첨단' not in key:
                emoji = "📚" if key == "교과" else "📋"
                title = f"**{emoji} {'교과' if key == '교과' else '종합'} 전형 최종 리스트**"
                st.write(title)
                if not df.empty:
                    # ranking 리스트의 순서대로 대학을 출력
                    for univ in ranking:
                        if univ in df['대학명'].unique():
                            st.write(f"**{univ}**")
                            univ_df = df[df['대학명'] == univ]
                            edited_df = st.data_editor(
                                univ_df,
                                hide_index=True,
                                column_config={
                                    "선택": st.column_config.CheckboxColumn(
                                        "선택",
                                        help="이 행을 선택하려면 체크하세요"
                                    )
                                },
                                disabled=univ_df.columns.drop('선택'),
                                key=f"editor_{key}_{univ}"
                            )
                            st.session_state[f'final_displayed_{key}_{univ}'] = edited_df
                else:
                    st.write("데이터가 없습니다.")

                # 교과 전형과 종합 전형 사이에 줄바꿈과 구분선 추가
                if i == 0:  # 첫 번째 iteration(교과 전형) 후에 줄바꿈과 구분선 추가
                    st.markdown("<br>", unsafe_allow_html=True)  # 줄바꿈
                    st.markdown("<hr>", unsafe_allow_html=True)  # 구분선
                    st.markdown("<br>", unsafe_allow_html=True)  # 줄바꿈

        # 신설 및 첨단학과 표시
        for key, df in st.session_state['final_results'].items():
            if '신설첨단' in key:
                emoji = "🔬" if '교과' in key else "🧬"
                title = f"**{emoji} {'교과' if '교과' in key else '종합'} 전형 신설 및 첨단학과**"
                st.write(title)
                if not df.empty:
                    edited_df = st.data_editor(
                        df,
                        hide_index=True,
                        column_config={
                            "선택": st.column_config.CheckboxColumn(
                                "선택",
                                help="이 행을 선택하려면 체크하세요"
                            )
                        },
                        disabled=df.columns.drop('선택'),
                        key=f"editor_{key}"
                    )
                    st.session_state[f'final_displayed_{key}'] = edited_df
                else:
                    st.write("데이터가 없습니다.")


    if st.button("리스트 확정", key='confirm_final_list_button'):
        final_selection = {}
        for key in st.session_state['final_results'].keys():
            if '신설첨단' in key:
                if f'final_displayed_{key}' in st.session_state:
                    df = st.session_state[f'final_displayed_{key}']
                    selected_df = df[df['선택']]
                    if not selected_df.empty:
                        final_selection[key] = selected_df
            else:
                selected_df = pd.DataFrame()
                for univ in st.session_state['final_results'][key]['대학명'].unique():
                    if f'final_displayed_{key}_{univ}' in st.session_state:
                        univ_df = st.session_state[f'final_displayed_{key}_{univ}']
                        selected_df = pd.concat([selected_df, univ_df[univ_df['선택']]])
                if not selected_df.empty:
                    final_selection[key] = selected_df

        if final_selection:
            st.session_state['final_selection'] = final_selection
            counts = {key: len(df) for key, df in final_selection.items()}
            st.success(
                f"교과 {counts.get('교과', 0)}개, 학종 {counts.get('학종', 0)}개, "
                f"교과 신설첨단 {counts.get('교과_신설첨단', 0)}개, 학종 신설첨단 {counts.get('학종_신설첨단', 0)}개 "
                f"저장 완료되었습니다.")
        else:
            st.warning("선택된 항목이 없습니다. 최소한 하나 이상의 항목을 선택해 주세요.")



if __name__ == "__main__":
    show_final_filtering()