
    /* 변수 설정 */
    const file_input =document.getElementById("file_input"); /* 파일 선택 */
    const url_input=document.getElementById("url_input"); /* 링크 입력 */
    const upload_start_button =document.getElementById("upload_start_button"); /* 업로드 버튼 */
    let selected_file = null; /* 선택된 파일 저장 */
    const file_name = document.getElementById("file_name");


/* 파일선택 */
   file_input.addEventListener("change", function(event) {
    selected_file = event.target.files[0]; /* 첫 번째 파일을 가져옴 */

    if (selected_file) {
        console.log("선택한 파일:", selected_file.name); /* 파일을 잘 선택했는지 확인 */
        file_name.textContent = selected_file.name; /* 선택한 파일 이름명 보여줌. */
        upload_start_button.disabled = false /* 업로드 버튼 활성화 */
    }
});

/* 파일 선택 버튼 클릭 */
const select_button = document.getElementById("select_button");

select_button.addEventListener("click", () => {
    file_input.click();
});


/* 업로드 버튼 클릭 */
upload_start_button.addEventListener("click", async function (event) {

    event.preventDefault(); /* 폼 제출 시 페이지 새로고침을 막는 행동 */


/* 파일 선택 */
    if (selected_file) { /* 파일이 있으면 */

        const form_data = new FormData(); /* multipart/form-data으로 보내야하므로  */

        form_data.append("file", selected_file); /* 데이터 추가 */

        try {

            const response = await fetch( /* 서버에 요청을 보냄 */
                "http://localhost:8000/api/v1/upload/file",
                {
                    method: "POST",/* 보내기 */
                    body: form_data /* 보낼 데이터 */
                }
            );
            if (!response.ok) {
                throw new Error("파일 업로드 실패");
            }

            const data = await response.json(); /* 서버가 보낸 응답을 자바스크립트 객체로 변환 */
            console.log(data); /* 콘솔에 데이터 출력 */

            alert("파일 업로드 성공");
            location.href = "../uploading/2.html";

        } catch (error) {

            console.error(error); /* 콘솔에 오류 출력 */

            alert("업로드 실패");

        }

        return;
    }

    



/* 링크 업로드 */
 const url = url_input.value.trim(); /* .value : 사용자가 입력한 값을 가져옴 */

    if (url !== "") { /* url이 비어있지않으면 실행 */

        try {

            const response = await fetch( /* url 업로드 API에 데이터를 보냄 */
                "http://localhost:8000/api/v1/upload/url",
                {
                    method: "POST", /* 보내기 */

                    headers: {
                        "Content-Type": "application/json" /* 서버에게 json 형식의 데이터를 보냄 */
                    },

                    body: JSON.stringify({ /* 문자열로 변환 */
                        url: url
                    })

                }
            );

            const data = await response.json();

            console.log(data); /* 서버에서 보내준 응답 출력 */

            alert("링크 업로드 성공");
        
        /* 오류 발생 시 */

        } catch (error) { 

            console.error(error);

            alert("업로드 실패");

        }

        return;
    }

    alert("파일을 선택하거나 링크를 입력해주세요.");
});

