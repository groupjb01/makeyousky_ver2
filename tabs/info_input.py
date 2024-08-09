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

    student_name = st.text_input("👤 학생 이름을 입력하세요")
    st.write(f"이름 : {student_name}")

    school_type = st.radio("🏫 고교 유형을 선택하세요", ["일반고", "학군지 일반고", "지역자사고", "전사고", "과학고", "외고"], index=0)

    field = st.multiselect("📚 계열을 선택하세요", ["인문", "자연"])

    detail_field_options = {
        "인문": [
            "경영", "경제", "교육", "국어국문", "국제", "기타언어", "데이터",
            "독일독어", "디자인", "무역", "법학", "사회복지", "사회학", "스페인어",
            "스포츠", "심리", "아동유아", "언론미디어", "언어학", "역사(사학)", "영어영문",
            "일본어", "자유전공", "정치외교", "종교", "중국어", "지리", "철학", "첨단",
            "프랑스어", "행정", "AI(인문)"
        ],
        "자연": [
            "간호", "건설", "건축", "기계", "물리", "반도체", "보건", "산업공학", "생명",
            "생활과학", "수의학", "수학", "스마트팜", "식품", "신약개발", "약학", "에너지",
            "의학", "전기전자", "지구과학", "치대", "컴공", "통계", "한의예", "헬스케어",
            "화생공", "화학", "환경"
        ]
    }

    detail_fields_selected = []
    for selected_field in field:
        with st.expander(f"📂 세부 계열을 선택하세요 ({selected_field})"):
            detail_fields = st.multiselect(f"세부 계열 ({selected_field})", detail_field_options[selected_field])
            detail_fields_selected.extend(detail_fields)
    st.write(f"선택된 세부 계열 : {', '.join(detail_fields_selected)}")

    score = st.number_input("📊 성적을 입력하세요", min_value=1.00, max_value=9.00, value=2.00, step=0.10)
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

    gender = st.radio("👤 성별을 선택하세요", ["남자", "여자"])

    admission_type = st.multiselect("📝 전형 구분을 선택하세요", ["교과", "종합"], default=["교과", "종합"])

    submit_button = st.button("정보 입력")

    if submit_button:
        adjustment_factor = SCHOOL_TYPE_ADJUSTMENT.get(school_type, 1.0)
        adjusted_score = max(score * adjustment_factor, 1.00)

        st.session_state['student_info'] = {
            'name': student_name,
            'school_type': school_type,
            'field': field,
            'detail_fields': detail_fields_selected,
            'score': round(score, 2),
            'adjusted_score': round(adjusted_score, 2),
            'lowest_ability': lowest_ability,
            'lowest_ability_code': lowest_ability_code,
            'non_subject_level': non_subject_level,
            'major_subjects_strong': major_subjects_strong,
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

if __name__ == "__main__":
    show_info_input()