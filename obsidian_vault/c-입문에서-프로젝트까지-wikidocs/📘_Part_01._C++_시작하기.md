---
url: "https://wikidocs.net/300272"
collected_at: "2026-06-14 05:24:06"
updated_at: "2026-06-14 05:25:11"
category: "AI/Software Engineering"
tags: [C++, 입문, Hello World, 기초 문법, cout, cin]
summary: "C++은 1980년대에 등장한 객체 지향 프로그래밍 언어로 빠른 실행 속도가 특징이며, 게임, AI, 로봇 제어, 임베디드 시스템 등 다양한 분야에서 사용된다. 문서는 C++ 프로그램의 기본 실행 흐름(소스 작성 → 컴파일 → 실행파일 생성 → 실행)을 설명하고 Hello, World! 출력 예제를 통해 #include <iostream>, using namespace std, main() 함수, cout, cin 등의 기초 요소를 단계별로 안내한다. 사용자 입력을 받아 인사말을 출력하는 미션과 나이 입력 확장 미션을 포함하며, main() 함수가 프로그램 시작점임을 강조한다."
source_title: "📘 Part 01. C++ 시작하기"
series: "c-입문에서-프로젝트까지-wikidocs"
series_title: "C++ 입문에서 프로젝트까지"
series_order: 1
---

# 📘 Part 01. C++ 시작하기

1. 개념 설명 (Concept)
C++은 1980년대에 등장한 프로그래밍 언어로, 빠른 실행 속도와 객체 지향 프로그래밍(OOP) 지원이 특징입니다. 게임, 인공지능, 로봇 제어, 임베디드 시스템까지 다양한 분야에서 활용되고 있습니다. 특히 Arduino와 ROS에서 로봇 제어 시 핵심 언어로 사용됩니다.

2. 그림 (Visual)
C++ 프로그램 실행 흐름: [소스코드 작성] → [컴파일] → [실행파일 생성] → [실행 결과]
소스코드(.cpp): 사람이 읽는 코드
컴파일: 기계어로 번역
실행파일(.exe / .out): CPU가 실행 가능한 파일
실행: 실제 동작 확인

3. 코드 예제 (Code Example)
#include <iostream>
using namespace std;

int main() {
    cout << "Hello, World!" << endl;
    return 0;
}

4. 실행 결과 (Output)
Hello, World!

5. 단계별 해설 (Step by Step)
#include <iostream> → 입출력 도구 불러오기
using namespace std; → std:: 생략
int main() → 프로그램 시작점
cout << "Hello, World!"; → 문자열 출력
return 0; → 정상 종료 알림

6. 응용 실습 (Practice Mission)
미션 1: 이름을 입력받아 "안녕하세요, [이름]님!" 출력
#include <iostream>
using namespace std;

int main() {
    string name;
    cout << "이름을 입력하세요: ";
    cin >> name;
    cout << "안녕하세요, " << name << "님!" << endl;
    return 0;
}

미션 2: 나이를 입력받아 "당신은 [나이]살이군요!" 출력하는 프로그램 작성

7. 요약 (Summary)
C++ 프로그램은 main() 함수에서 시작된다. #include <iostream> + cout으로 화면 출력이 가능하다. cin을 활용해 사용자 입력을 받을 수 있다.

### 🔗 연결된 지식 네트워크
- [[📘 Part 02. 기본 문법 (변수와 자료형, 연산자)]]: 동일한 C++ 입문 시리즈의 이전 파트로, Hello World와 기본 입출력 흐름을 이어서 다룸
- [[📘 Part 03. 조건문과 반복문 (제어문)]]: 동일 시리즈의 입문 파트로 C++ 기본 실행 흐름과 입출력을 다룸
- [[📘 Part 04. 클래스와 객체 지향 기초]]: 같은 C++ 입문 시리즈의 이전 파트
