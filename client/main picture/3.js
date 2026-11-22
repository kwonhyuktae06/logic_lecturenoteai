 

/* =========================
   모든 페이지 숨기기
========================= */

function hideAllPages() {

    content.style.display = "none";
    timelinePage.style.display = "none";
    summaryPage.style.display = "none";
    quizPage.style.display = "none";
    wrongnotePage.style.display = "none";

}
        /* =====================================
           테스트용 타임라인 데이터
        ===================================== */

        const timelineData = [

            {
                time: 0,
                title: "강의 소개"
            },

            {
                time: 5,
                title: "명사"
            },

            {
                time: 10,
                title: "가산명사"
            },

            {
                time: 15,
                title: "불가산 명사"
            }

        ];



        /* =====================================
           영상
        ===================================== */

        const video = document.querySelector("#video");



        /* =====================================
           초 → MM:SS
        ===================================== */

        function formatTime(seconds) {

            const minutes =
                Math.floor(seconds / 60);

            const secondsLeft =
                Math.floor(seconds % 60);

            return (
                String(minutes).padStart(2, "0")
                + ":"
                + String(secondsLeft).padStart(2, "0")
            );

        }



        /* =====================================
           타임라인
        ===================================== */

        const timeline =
            document.querySelector(".timeline");



        timelineData.forEach((item, index) => {

            const timelineItem =
                document.createElement("div");


            timelineItem.classList.add(
                "timeline_item"
            );


            timelineItem.innerHTML = `

                <div class="timeline_time">

                    ${formatTime(item.time)}

                </div>


                <div class="timeline_content">

                    <h4>
                        ${item.title}
                    </h4>

                </div>

            `;



            /* ===============================
               타임라인 클릭
            =============================== */

            timelineItem.addEventListener(
                "click",
                () => {

                    /*
                     * 해당 타임라인의
                     * 영상 시간으로 이동
                     */

                    video.currentTime =
                        item.time;


                    /*
                     * 영상 자동 재생
                     */

                    video.play();


                    /*
                     * 현재 선택된 항목 표시
                     */

                    document
                        .querySelectorAll(
                            ".timeline_item"
                        )
                        .forEach(item => {

                            item.classList.remove(
                                "active"
                            );

                        });


                    timelineItem.classList.add(
                        "active"
                    );

                }
            );


            timeline.appendChild(
                timelineItem
            );

        });



        /* =====================================
           영상 재생 중 현재 타임라인 표시
        ===================================== */

        video.addEventListener(
            "timeupdate",
            () => {

                let currentIndex = 0;


                /*
                 * 현재 영상 시간이
                 * 어느 구간에 속하는지 찾음
                 */

                for (
                    let i = 0;
                    i < timelineData.length;
                    i++
                ) {

                    if (
                        video.currentTime
                        >= timelineData[i].time
                    ) {

                        currentIndex = i;

                    } else {

                        break;

                    }

                }


                /*
                 * 모든 항목의 active 제거
                 */

                document
                    .querySelectorAll(
                        ".timeline_item"
                    )
                    .forEach(
                        item => {

                            item.classList.remove(
                                "active"
                            );

                        }
                    );


                /*
                 * 현재 항목 active
                 */

                const items =
                    document.querySelectorAll(
                        ".timeline_item"
                    );


                if (items[currentIndex]) {

                    items[currentIndex]
                        .classList.add(
                            "active"
                        );

                }

            }
        );



        /* =====================================
           타임라인 버튼
        ===================================== */

        const timelineButton =
            document.querySelector(
                "#timeline_button"
            );


        const timelinePage =
            document.querySelector(
                ".timeline_page"
            );


        const content =
            document.querySelector(
                ".content"
            );


        timelineButton.addEventListener(
            "click",
            () => {

                hideAllPages();
                   

                timelinePage.style.display =
                    "block";

            }
        );



        /* =====================================
           홈 버튼
        ===================================== */

        const homeButton =
            document.querySelector(
                "#home_button"
            );


        homeButton.addEventListener(
            "click",
            () => {

                hideAllPages();

                content.style.display =
                    "block";

            }
        );


  /* =========================
             핵심요약 화면
        ========================= */


const summaryButton = 
    document.querySelector("#summary_button");

const summaryPage = 
    document.querySelector(".summary_page");



summaryButton.addEventListener(
    "click", 
    () => {

        hideAllPages();
         summaryPage.style.display = "block";
});


/* =========================
   핵심요약 노트 데이터
========================= */

// 임시 테스트 데이터
// 추후 파이프라인에서 전달받은 데이터로 교체

const summaryLectureData = {

    title: "프로그래밍 기초 강의",

    overview:
        "이번 강의에서는 프로그래밍의 기본 개념과 변수, 자료형, 연산자에 대해 학습합니다.\n\n프로그램을 작성하기 위해서는 데이터를 저장하고 처리하는 방법을 이해해야 합니다.",

    subtopics: [

        {
            title: "1. 프로그래밍의 개념",

            time: "00:00",

            content:
                "프로그래밍은 컴퓨터가 수행할 작업을 명령어로 작성하는 과정이다.\n\n프로그램은 문제를 해결하기 위한 명령어들의 집합이다."
        },

        {
            title: "2. 변수와 자료형",

            time: "05:20",

            content:
                "변수는 데이터를 저장하기 위한 공간이다.\n\n자료형은 변수에 저장되는 데이터의 종류를 의미한다.\n\n대표적인 자료형에는 정수형, 실수형, 문자열형 등이 있다."
        },

        {
            title: "3. 연산자",

            time: "12:35",

            content:
                "연산자는 데이터를 계산하거나 비교하기 위해 사용하는 기호이다.\n\n산술 연산자에는 +, -, *, / 등이 있으며 비교 연산자는 두 값을 비교할 때 사용한다."
        },

        {
            title: "4. 조건문과 반복문",

            time: "20:10",

            content:
                "조건문은 조건에 따라 서로 다른 명령을 실행한다.\n\n반복문은 특정 조건이 만족되는 동안 명령을 반복해서 실행한다."
        }

    ]

};


/* =========================
   핵심요약 화면 요소 가져오기
========================= */

const summaryLectureTitle =
    document.querySelector("#summary_lecture_title");

const summaryOverview =
    document.querySelector("#summary_overview_content");

const summaryContent =
    document.querySelector("#summary_content");


/* =========================
   핵심요약 화면 출력
========================= */

function renderSummary() {

    // 강의 제목 출력
    summaryLectureTitle.textContent =
        summaryLectureData.title;


    // 전체 핵심 내용 출력
    summaryOverview.textContent =
        summaryLectureData.overview;


    // 기존 요약 카드 초기화
    summaryContent.innerHTML = "";


    // 소주제별 카드 생성
    summaryLectureData.subtopics.forEach(
        (item) => {

            // 카드 생성
            const topicCard =
                document.createElement("div"); //HTML 요소인 div 생성

            topicCard.className = "summary_topic"; // div에 css 클래스 이름 지정


            // 소주제 제목
            const topicTitle =
                document.createElement("div");

            topicTitle.className = "summary_subtopic";

            topicTitle.textContent =
                item.title;


            // 강의 시간
            const topicTime =
                document.createElement("span");

            topicTime.className = "summary_time";

            topicTime.textContent =
                item.time;


            // 요약 내용
            const topicText =
                document.createElement("div");

            topicText.className = "summary_text";

            topicText.textContent =
                item.content;


            // 카드에 요소 추가
            topicCard.appendChild(topicTitle);

            topicCard.appendChild(topicTime);

            topicCard.appendChild(topicText);


            // 화면에 카드 추가
            summaryContent.appendChild(topicCard);

        }
    );

}


/* =========================
   핵심요약 화면 실행
========================= */

renderSummary();

  /* =========================
            퀴즈 화면
        ========================= */


const quizButton = 
    document.querySelector("#quiz_button");

const quizPage = 
    document.querySelector(".quiz_page");



quizButton.addEventListener(
    "click", 
    () => {

        hideAllPages();
         quizPage.style.display = "block";
});

  /* =========================
            오답노트 화면
        ========================= */


const wrongnoteButton = 
    document.querySelector("#wrongnote_button");

const wrongnotePage = 
    document.querySelector(".wrongnote_page");



wrongnoteButton.addEventListener(
    "click", 
    () => {

        hideAllPages();
         wrongnotePage.style.display = "block";
});


/* =========================
   오답노트 데이터
========================= */

// 임시 테스트 데이터
// 추후 퀴즈 파이프라인 데이터로 교체

const wrongNoteData = [

    {
        id: 1,

        question:
            "변수에 대한 설명으로 올바른 것은?",

        userAnswer:
            "프로그램을 실행하는 명령어",

        correctAnswer:
            "데이터를 저장하는 공간",

        explanation:
            "변수는 데이터를 저장하기 위한 메모리 공간이다. 변수에 저장된 값은 프로그램 실행 중 변경할 수 있다.",

        time: "05:20",

        completed: false
    },


    {
        id: 2,

        question:
            "다음 중 정수형 자료형에 해당하는 것은?",

        userAnswer:
            "3.14",

        correctAnswer:
            "10",

        explanation:
            "정수형은 소수점이 없는 숫자를 의미한다. 10은 정수형이고 3.14는 실수형에 해당한다.",

        time: "08:15",

        completed: false
    },


    {
        id: 3,

        question:
            "반복문을 사용하는 주된 목적은 무엇인가?",

        userAnswer:
            "조건에 따라 다른 명령 실행",

        correctAnswer:
            "특정 명령을 반복해서 실행",

        explanation:
            "반복문은 특정 조건이 만족되는 동안 명령문을 반복해서 실행하기 위해 사용한다.",

        time: "20:10",

        completed: false
    }

];


/* =========================
   오답노트 HTML 요소
========================= */

const wrongNoteList =
    document.querySelector("#wrongnote_list");

const wrongNoteTotal =
    document.querySelector("#wrongnote_total");

const wrongNoteCompleted =
    document.querySelector("#wrongnote_completed");

const wrongNoteRemaining =
    document.querySelector("#wrongnote_remaining");

const wrongNoteCount =
    document.querySelector("#wrongnote_count");


/* =========================
   오답 통계 업데이트
========================= */

function updateWrongNoteStats() {

    // 전체 오답 개수
    const total =
        wrongNoteData.length;


    // 복습 완료 개수
    const completed =
        wrongNoteData.filter(
            (item) => item.completed
        ).length;


    // 복습이 필요한 개수
    const remaining =
        total - completed;


    // 화면에 통계 출력
    wrongNoteTotal.textContent = total;

    wrongNoteCompleted.textContent =
        completed;

    wrongNoteRemaining.textContent =
        remaining;

    wrongNoteCount.textContent =
        `총 ${total}문제`;

}


/* =========================
   오답 문제 카드 생성
========================= */

function renderWrongNote() {

    // 기존 카드 초기화
    wrongNoteList.innerHTML = "";


    // 오답 데이터 반복
    wrongNoteData.forEach(
        (item) => {

            // 문제 카드 생성
            const card =
                document.createElement("div");

            card.className = "wrongnote_card";


            // 카드 상단
            const header =
                document.createElement("div");

            header.className =
                "wrongnote_card_header";


            // 문제 번호
            const number =
                document.createElement("span");

            number.className =
                "wrongnote_number";

            number.textContent =
                `문제 ${item.id}`;


            // 복습 상태
            const status =
                document.createElement("span");

            status.className =
                item.completed
                    ? "wrongnote_status completed"
                    : "wrongnote_status";

            status.textContent =
                item.completed
                    ? "복습 완료"
                    : "복습 필요";


            header.appendChild(number);

            header.appendChild(status);


            // 문제 내용
            const question =
                document.createElement("div");

            question.className =
                "wrongnote_question";

            question.textContent =
                item.question;


            // 답안 영역
            const answer =
                document.createElement("div");

            answer.className =
                "wrongnote_answer";


            // 내가 선택한 답
            const userAnswer =
                document.createElement("div");

            userAnswer.className =
                "wrongnote_answer_box wrongnote_user_answer";

            userAnswer.textContent =
                `내가 선택한 답 : ${item.userAnswer}`;


            // 정답
            const correctAnswer =
                document.createElement("div");

            correctAnswer.className =
                "wrongnote_answer_box wrongnote_correct_answer";

            correctAnswer.textContent =
                `정답 : ${item.correctAnswer}`;


            answer.appendChild(userAnswer);

            answer.appendChild(correctAnswer);


            // 정답 해설
            const explanation =
                document.createElement("div");

            explanation.className =
                "wrongnote_explanation";


            const explanationTitle =
                document.createElement("h4");

            explanationTitle.textContent =
                "💡 정답 해설";


            const explanationText =
                document.createElement("p");

            explanationText.textContent =
                item.explanation;


            explanation.appendChild(explanationTitle);

            explanation.appendChild(explanationText);


            // 강의 시간
            const time =
                document.createElement("div");

            time.className =
                "wrongnote_time";

            time.textContent =
                `📍 관련 강의 시간 : ${item.time}`;


            // 복습 완료 버튼
            const reviewButton =
                document.createElement("button");

            reviewButton.className =
                "wrongnote_review_button";

            reviewButton.textContent =
                item.completed
                    ? "복습 완료"
                    : "복습 완료하기";


            reviewButton.disabled =
                item.completed;


            // 복습 완료 버튼 이벤트
            reviewButton.addEventListener(
                "click",
                () => {

                    // 복습 상태 변경
                    item.completed = true;


                    // 화면 다시 출력
                    renderWrongNote();

                }
            );


            // 카드에 요소 추가
            card.appendChild(header);

            card.appendChild(question);

            card.appendChild(answer);

            card.appendChild(explanation);

            card.appendChild(time);

            card.appendChild(reviewButton);


            // 오답 목록에 카드 추가
            wrongNoteList.appendChild(card);

        }
    );


    // 통계 업데이트
    updateWrongNoteStats();

}


/* =========================
   오답노트 화면 실행
========================= */

renderWrongNote();
