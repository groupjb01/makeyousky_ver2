import streamlit as st
import pandas as pd
from data_loader import ranking

def sort_universities(df, sort_option, sort_order):
    if sort_option == '경쟁률 백분위':
        return df.sort_values('2024년_경쟁률백분위', ascending=(sort_order == '오름차순'))
    elif sort_option == '경쟁률 변동(%)':
        return df.sort_values('2024년_경쟁률변동(%)', ascending=(sort_order == '오름차순'))
    elif sort_option == '3개년 경쟁률 백분위 평균':
        return df.sort_values('3개년_경쟁률_평균', ascending=(sort_order == '오름차순'))
    elif sort_option == '입결70% 변동(%)':
        return df.sort_values('2024년_입결70%변동(%)', ascending=(sort_order == '오름차순'))
    elif sort_option == '3개년 입결70% 평균':
        return df.sort_values('3개년_입결70%_평균', ascending=(sort_order == '오름차순'))
    elif sort_option == '충원율(%)':
        return df.sort_values('2024년_충원율(%)', ascending=(sort_order == '오름차순'))
    elif sort_option == '3개년 충원율 평균':
        return df.sort_values('3개년_충원율_평균', ascending=(sort_order == '오름차순'))
    elif sort_option == '수능최저':
        return df.sort_values('2025년_수능최저코드', ascending=(sort_order == '오름차순'))
    else:
        return df

def order_by_ranking(df):
    if '대학명' not in df.columns:
        st.warning("데이터프레임에 '대학명' 열이 없습니다.")
        return df

    ranking = ['서울대학교', '연세대학교', '고려대학교', 'KAIST', 'POSTECH', '서강대학교', '성균관대학교', '한양대학교', '중앙대학교', '경희대학교', '한국외국어대학교',
               '서울시립대학교', '건국대학교', '동국대학교', '홍익대학교', '국민대학교', '숭실대학교', '세종대학교', '단국대학교', 'DGIST', 'UNIST', 'GIST',
               '이화여자대학교', '성신여자대학교', '숙명여자대학교', '광운대학교', '명지대학교', '상명대학교', '가천대학교', '가톨릭대학교']
    df['ranking'] = df['대학명'].apply(lambda x: ranking.index(x) if x in ranking else len(ranking))
    return df.sort_values('ranking').drop('ranking', axis=1)


def order_by_ranking(df):
    if '대학명' not in df.columns:
        st.warning("데이터프레임에 '대학명' 열이 없습니다.")
        return df

    df['ranking'] = df['대학명'].apply(lambda x: ranking.index(x) if x in ranking else len(ranking))
    return df.sort_values('ranking').drop('ranking', axis=1)


def reorder_columns(df):
    first_columns = ['선택', '대학명', '전형명', '모집단위']
    excluded_columns = ['No.', '계열상세']
    other_columns = [col for col in df.columns if col not in first_columns + excluded_columns]
    return df[first_columns + other_columns]

def show_final_filtering():
    st.info("교과, 학종 필터링 결과를 조건에 따라 정렬하여 리스트별 최대 10개의 대학을 선정합니다.")

    if 'saved_subject_results' not in st.session_state or 'saved_comprehensive_results' not in st.session_state:
        st.warning("교과 필터링과 학종 필터링을 먼저 완료해주세요.")
        return

    saved_subject_results = reorder_columns(st.session_state['saved_subject_results'])
    saved_comprehensive_results = reorder_columns(st.session_state['saved_comprehensive_results'])

    # 신설 및 첨단학과 리스트 추출
    subject_new_advanced = saved_subject_results[
        (saved_subject_results['신설'] != '0') | (saved_subject_results['첨단융합'] == 1)]
    comprehensive_new_advanced = saved_comprehensive_results[
        (saved_comprehensive_results['신설'] != '0') | (saved_comprehensive_results['첨단융합'] == 1)]

    # 기존 리스트에서 신설 및 첨단학과 제외
    saved_subject_results = saved_subject_results[
        (saved_subject_results['신설'] == '0') & (saved_subject_results['첨단융합'] != 1)]
    saved_comprehensive_results = saved_comprehensive_results[
        (saved_comprehensive_results['신설'] == '0') & (saved_comprehensive_results['첨단융합'] != 1)]

    if st.button("전형별 저장 데이터 보기"):
        st.markdown("---")
        st.markdown("&nbsp;")
        st.subheader("1️⃣  전형별 저장 데이터 보기")

        st.subheader("📚 교과 지원 리스트")
        if not saved_subject_results.empty:
            df = order_by_ranking(saved_subject_results)
            df['선택'] = True  # '선택' 컬럼 추가
            for univ in df['대학명'].unique():
                st.write(f"**{univ}**")
                univ_df = df[df['대학명'] == univ]
                st.dataframe(univ_df)
        else:
            st.warning("교과 전형 데이터가 없습니다.")

        st.markdown("<hr style='border-top: 3px dashed #bbb;'>", unsafe_allow_html=True)

        st.subheader("📋 학종 지원 리스트")
        if not saved_comprehensive_results.empty:
            df = order_by_ranking(saved_comprehensive_results)
            df['선택'] = True  # '선택' 컬럼 추가
            for univ in df['대학명'].unique():
                st.write(f"**{univ}**")
                univ_df = df[df['대학명'] == univ]
                st.dataframe(univ_df)
        else:
            st.warning("학종 전형 데이터가 없습니다.")


    admission_types = ['교과', '학종']
    sort_options = [
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

    if st.button("최종 필터링 적용", key='apply_final_filter_button'):
        final_results = {}

        admission_data = [
            ('교과', saved_subject_results, subject_new_advanced),
            ('학종', saved_comprehensive_results, comprehensive_new_advanced)
        ]

        for admission_type, results, new_advanced in admission_data:
            if not results.empty or not new_advanced.empty:
                sort_option = st.session_state[f'{admission_type}_sort']
                sort_order = st.session_state[f'{admission_type}_order']

                # 일반 학과 정렬
                df = sort_universities(results, sort_option, sort_order)
                df = order_by_ranking(df)
                df['선택'] = False  # 기본값을 False로 변경
                df['구분'] = '일반'

                # 신설 및 첨단학과 정렬
                new_advanced = order_by_ranking(new_advanced)
                new_advanced['선택'] = True  # 신설첨단학과는 True로 유지
                new_advanced['구분'] = '신설/첨단'

                # 일반 학과와 신설/첨단학과 합치기
                combined_df = pd.concat([df, new_advanced])
                combined_df = order_by_ranking(combined_df)

                final_results[admission_type] = combined_df.head(20)  # 20개로 증가
                final_results[f'{admission_type}_신설첨단'] = new_advanced
            else:
                st.warning(f"{admission_type} 전형 리스트에 데이터가 없습니다.")

        st.session_state['final_results'] = final_results
        st.success("최종 필터링이 적용되었습니다.")

    if 'final_results' in st.session_state:
        st.subheader("최종 필터링 결과")
        for key, df in st.session_state['final_results'].items():
            if '신설첨단' in key:
                emoji = "🔬" if '교과' in key else "🧬"
                title = f"**{emoji} {key.split('_')[0]} 전형 신설 및 첨단학과**"
            else:
                emoji = "📚" if key == "교과" else "📋"
                title = f"**{emoji} {key} 전형 최종 리스트**"

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
                st.session_state['final_results'][key] = edited_df
            else:
                st.write("데이터가 없습니다.")

        if st.button("리스트 확정", key='confirm_final_list_button'):
            final_selection = {}
            for key, df in st.session_state['final_results'].items():
                selected_df = df[df['선택']]
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