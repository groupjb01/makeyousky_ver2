import streamlit as st
from tabs import info_input, subject_filtering, comprehensive_filtering, final_filtering, report_generation
from data_loader import data, lowest_ability_codes
from data_loader import load_data, lowest_ability_codes, additional_data

def main():
    st.title("🖋️️ 지략 수시전략 컨설팅 지원 시스템 ")
    st.markdown("&nbsp;")
    tabs = st.tabs(["정보입력", "교과 필터링", "학종 필터링", "최종 필터링", "보고서 작성"])
    st.session_state['additional_data'] = additional_data
    # 데이터 로드
    if 'all_data' not in st.session_state:
        st.session_state['all_data'] = load_data('data_240806_1610.xlsx')

    with tabs[0]:
        info_input.show_info_input()
    with tabs[1]:
        subject_filtering.show_subject_filtering()
    with tabs[2]:
        comprehensive_filtering.show_comprehensive_filtering()
    with tabs[3]:
        final_filtering.show_final_filtering()
    with tabs[4]:
        report_generation.show_report_generation()

if __name__ == "__main__":
    main()