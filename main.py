import streamlit as st
import yaml
import streamlit_authenticator as stauth

with open('config.yaml') as file:
    config = yaml.load(file, Loader=stauth.SafeLoader)

## yaml 파일 데이터로 객체 생성
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

## 로그인 위젯 렌더링
## log(in/out)(로그인 위젯 문구, 버튼 위치)
## 버튼 위치 = "main" or "sidebar"
name, authentication_status, username = authenticator.login("Login","main")

# authentication_status : 인증 상태 (실패=>False, 값없음=>None, 성공=>True)
if authentication_status == False:
    st.error("Username/password is incorrect")

if authentication_status == None:
    st.warning("Please enter your username and password")

if authentication_status:
    authenticator.logout("Logout","sidebar")
    st.sidebar.title(f"Welcome {name}")
    
    ## 로그인 후 기능들 작성 ##

    # 페이지 설정을 스크립트의 가장 첫 부분으로 이동
    st.set_page_config(page_title="지략 수시전략 컨설팅 지원 시스템", layout="wide")
    
    from tabs import info_input, subject_filtering, comprehensive_filtering, final_filtering, report_generation, direct_upload
    from data_loader import data, lowest_ability_codes
    from data_loader import load_data, lowest_ability_codes, additional_data
    
    def main():
        st.title("🖋️️ 지략 수시전략 컨설팅 지원 시스템 ")
        st.markdown("&nbsp;")
        tabs = st.tabs(["정보입력", "교과 필터링", "학종 필터링", "최종 필터링", "보고서 작성", "직접 데이터 업로드"])
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
        with tabs[5]:
            direct_upload.show_direct_upload()
    
    if __name__ == "__main__":
        main()
