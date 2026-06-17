---
url: "https://wikidocs.net/300283"
collected_at: "2026-06-14 05:24:08"
updated_at: "2026-06-14 05:25:26"
category: "AI/Software Engineering"
tags: [C++, 조건문, 반복문, 제어문, if, for, while, 기초 문법]
summary: "C++의 제어문을 다루는 문서로, if, if-else, else if, switch 조건문과 for, while, do-while 반복문의 개념과 사용법을 설명한다. 각 문법의 동작 흐름을 시각화하고, 점수에 따른 학점 판별 및 1~5 출력 예제를 통해 실제 코드를 제시한다. 구구단 출력기와 1~100 숫자 맞추기 게임 실습 미션을 통해 사용자 입력 기반 반복 제어 프로그램 작성법을 안내하며, 실행 결과와 단계별 해설을 제공한다."
source_title: "📘 Part 03. 조건문과 반복문 (제어문)"
series: "c-입문에서-프로젝트까지-wikidocs"
series_title: "C++ 입문에서 프로젝트까지"
series_order: 3
---

# 📘 Part 03. 조건문과 반복문 (제어문)

1. 개념 설명 (Concept)
조건문 (if, switch)
특정 조건이 참(true)인지 거짓(false)인지에 따라 실행 흐름을 제어하는 문법
if 문: 조건이 참일 때만 실행
if ~ else 문: 조건이 참/거짓일 때 각각 실행
if ~ else if ~ else 문: 여러 조건을 순차적으로 검사
switch 문: 하나의 변수 값에 따라 분기 실행 (정수/문자형에 주로 사용)

반복문 (for, while)
같은 동작을 여러 번 반복할 때 사용
for 문: 반복 횟수가 명확할 때 사용
while 문: 조건이 참인 동안 계속 반복
do ~ while 문: 최소 1회 실행 후 조건 검사

2. 그림 (Visual)
조건문 흐름도 (if ~ else)
조건식 → 참 → 실행문1
       ↘ 거짓 → 실행문2

반복문 흐름도 (for)
초기식 → [조건 검사] → 참 → 실행문 → 증감식 → [조건 검사] ...
             ↘ 거짓 → 반복 종료

3. 코드 예제 (Code Example)
조건문 예제
#include <iostream>
using namespace std;

int main() {
    int score;
    cout << "점수를 입력하세요: ";
    cin >> score;

    if (score >= 90) {
        cout << "A 학점" << endl;
    } else if (score >= 80) {
        cout << "B 학점" << endl;
    } else if (score >= 70) {
        cout << "C 학점" << endl;
    } else {
        cout << "F 학점" << endl;
    }

    return 0;
}

반복문 예제
#include <iostream>
using namespace std;

int main() {
    // 1부터 5까지 출력
    for (int i = 1; i <= 5; i++) {
        cout << i << " ";
    }
    cout << endl;

    // while 문: 1부터 5까지 출력
    int j = 1;
    while (j <= 5) {
        cout << j << " ";
        j++;
    }
    cout << endl;

    return 0;
}

4. 실행 결과 (Output)
점수를 입력하세요: 85
B 학점

1 2 3 4 5 
1 2 3 4 5 

5. 단계별 해설 (Step by Step)

if (score >= 90) → 조건이 참이면 "A 학점" 출력
else if (score >= 80) → 두 번째 조건 검사
else → 모든 조건이 거짓일 때 실행
for (int i = 1; i <= 5; i++) → i 값을 1씩 증가시키며 반복
while (j <= 5) → j가 5 이하인 동안 반복 실행

6. 응용 실습 (Practice Mission)
💡 미션 1: 구구단 출력기
사용자로부터 정수를 입력받아 해당 단의 구구단을 출력
#include <iostream>
using namespace std;

int main() {
    int n;
    cout << "구구단 단수를 입력하세요: ";
    cin >> n;

    for (int i = 1; i <= 9; i++) {
        cout << n << " x " << i << " = " << n * i << endl;
    }

    return 0;
}

실행 예시
구구단 단수를 입력하세요: 3
3 x 1 = 3
3 x 2 = 6
...
3 x 9 = 27

💡 미션 2 (확장): 숫자 맞추기 게임
1부터 100 사이의 랜덤 숫자를 맞출 때까지 반복 입력받는 프로그램
(힌트: #include <cstdlib>, #include <ctime> 사용)
#include <iostream>
#include <cstdlib>
#include <ctime>
using namespace std;

int main() {
    srand(time(0));          // 랜덤 시드 설정
    int target = rand() % 100 + 1;  // 1~100 난수
    int guess;

    do {
        cout << "숫자를 입력하세요 (1~100): ";
        cin >> guess;

        if (guess > target) {
            cout << "더 작은 수입니다." << endl;
        } else if (guess < target) {
            cout << "더 큰 수입니다." << endl;
        } else {
            cout << "정답입니다!" << endl;
        }
    } while (guess != target);

    return 0;
}

7. 요약 (Summary)

조건문: if, if~else, else if, switch 로 프로그램 흐름 제어
반복문: for, while, do~while 로 반복 작업 수행
조건문과 반복문을 사용하면 프로그램이 훨씬 유연해진다.
구구단, 숫자 맞추기 게임 같은 예제로 제어문을 실제 연습할 수 있다.
### 🔗 연결된 지식 네트워크
- [[📘 Part 02. 기본 문법 (변수와 자료형, 연산자)]]: 동일 시리즈의 이전 파트로 변수, 자료형, 연산자 학습을 이어 제어문을 다룸
- [[📘 Part 01. C++ 시작하기]]: 동일 시리즈의 입문 파트로 C++ 기본 실행 흐름과 입출력을 다룸
- [[📘 Part 05. 배열, 포인터, 참조]]: 동일 시리즈의 이전 파트로 반복문을 이용한 배열 처리 예제와 연계된다.
- [[📘 Part 04. 클래스와 객체 지향 기초]]: 같은 C++ 입문 시리즈의 직전 파트
