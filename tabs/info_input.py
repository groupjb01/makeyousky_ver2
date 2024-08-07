import streamlit as st
from data_loader import lowest_ability_codes, SCHOOL_TYPE_ADJUSTMENT, lowest_ability_ui_options


def show_info_input():
    st.markdown(
        """
        <style>
        [data-testid="stTabs"] button {
            flex: 1;
        }
        .stButton button {
            display: block;
            margin: 0 auto;
        }
        </style>
        """, unsafe_allow_html=True
    )
    st.info("수시전략 도출에 필요한 정보를 입력합니다.")

    school_type = st.radio("🏫 고교 유형을 선택하세요", ["일반고", "학군지 일반고", "지역자사고", "전사고", "과학고", "외고"], index=0)
    field = st.multiselect("📚 계열을 선택하세요", ["인문", "자연"])

    detail_field_options = {
        "인문": ["경영", "경제", "행정", "정치외교", "심리", "국어국문", "영어영문", "독일독어", "중국어", "일본어", "스페인어", "프랑스어", "기타언어", "언어학",
               "철학", "사회학", "사회복지", "아동유아", "역사(사학)", "교육", "지리", "언론미디어", "종교", "데이터", "무역", "국제", "법학", "AI(인문)",
               "디자인", "보건", "첨단", "스포츠", "자유전공"],
        "자연": ["간호", "건축", "건설", "물리", "생명", "화생공", "환경", "산업공학", "교육", "수학", "수의학", "식품", "약학", "에너지", "화학", "디자인",
               "의학", "전기전자", "기계", "지구과학", "컴공", "반도체", "신약개발", "헬스케어", "치대", "통계", "스마트팜", "보건", "한의예", "자유전공"],
        "예체능": ["스포츠", "디자인", "무용", "연극", "영화", "음악", "미술", "자유전공"]
    }

    detail_fields_selected = []
    for selected_field in field:
        with st.expander(f"📂 세부 계열을 선택하세요 ({selected_field})"):
            detail_fields = st.multiselect(f"세부 계열 ({selected_field})", detail_field_options[selected_field])
            detail_fields_selected.extend(detail_fields)

    major_interest = st.text_input("🎓 희망 전공을 입력하세요 (쉼표로 구분)")

    score = st.number_input("📊 성적을 입력하세요", min_value=1.00, max_value=9.00, step=0.01)
    if school_type in ["갓반고", "자사고"]:
        adjusted_score = max(score * 0.9, 1.00)
        st.write(f"입력한 성적: {score:.2f}, 조정된 성적: {adjusted_score:.2f}")
    else:
        adjusted_score = score
        st.write(f"입력한 성적: {score:.2f}")

    lowest_ability = st.selectbox("📉 수능최저 역량을 선택하세요", lowest_ability_ui_options)
    lowest_ability_code = lowest_ability_codes[lowest_ability]


    non_subject_level = st.radio("📒 비교과 활동 수준을 선택하세요", ["상", "중", "하"], index=1)
    major_subjects_strong = st.radio("주요과목 강함", ["YES", "NO"], index=1)

    high_score_factor = st.slider("🔧 상향 성적 배수를 선택하세요", min_value=0.1, max_value=0.9, step=0.1, value=0.7)
    low_score_factor = st.slider("🔧 안정 성적 배수를 선택하세요", min_value=1.1, max_value=1.5, step=0.1, value=1.3)
    gender = st.radio("👤 성별을 선택하세요", ["남자", "여자"])
    admission_type = st.multiselect("📝 전형 구분을 선택하세요", ["교과", "종합"], default=["교과", "종합"])

    submit_button = st.button("정보 입력")

    if submit_button:
        adjustment_factor = SCHOOL_TYPE_ADJUSTMENT.get(school_type, 1.0)
        adjusted_score = max(score * adjustment_factor, 1.00)

        st.session_state['student_info'] = {
            'school_type': school_type,
            'field': field,
            'detail_fields': detail_fields_selected,
            'major_interest': major_interest,
            'score': score,
            'adjusted_score': adjusted_score,
            'lowest_ability': lowest_ability,
            'lowest_ability_code': lowest_ability_code,
            'non_subject_level': non_subject_level,
            'major_subjects_strong': major_subjects_strong,
            'high_score_factor': high_score_factor,
            'low_score_factor': low_score_factor,
            'gender': gender,
            'admission_type': admission_type
        }

        st.success("아래와 같이 정보 입력이 완료되었습니다. 교과 필터링 탭으로 이동하세요.")
        st.write(st.session_state['student_info'])

        st.markdown("""
            <style>
            .stButton button {
                background-color: #4CAF50;
                color: white;
            }
            </style>
            """, unsafe_allow_html=True)