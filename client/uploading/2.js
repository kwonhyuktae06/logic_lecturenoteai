

const progressBar = document.querySelector("#progress");
const progressText = document.querySelector("#progress_text");

let progress = 0;

const timer = setInterval(() => {

    progress += 1;

    // 진행 바 너비 변경
    progressBar.style.width = progress + "%";

    // 진행률 텍스트 변경
    progressText.textContent =
        "분석 중... " + progress + "%";


    // 100%가 되면 종료
    if (progress >= 100) {

        clearInterval(timer);

        progressText.textContent =
            "분석 완료! 100%";

    }

}, 100);

