---
url: "https://wikidocs.net/300281"
collected_at: "2026-06-14 05:24:06"
updated_at: "2026-06-14 05:25:18"
category: "AI/Software Engineering"
tags: [C++, 변수, 자료형, 연산자, 기초 문법, cin, cout]
summary: "C++의 기본 문법으로 변수 개념, 주요 자료형(int, double, char, bool, string)과 산술·관계·논리·대입 연산자를 설명한다. 변수가 메모리에 이름표를 붙여 데이터를 저장하는 방식과 각 자료형의 사용 예를 제시하며, cout과 cin을 이용한 입출력 방법을 다룬다. 실제 코드 예제를 통해 정수·실수·문자·논리형 변수 선언과 산술 연산(% 포함)을 보여주고, bool 값이 1/0으로 출력되는 점을 주의한다. 계산기와 BMI 계산기 미션을 통해 사용자 입력을 받아 연산 결과를 출력하는 실습을 제공하며, cin을 활용한 상호작용 프로그램 작성법을 익힌다."
source_title: "📘 Part 02. 기본 문법 (변수와 자료형, 연산자)"
series: "c-입문에서-프로젝트까지-wikidocs"
series_title: "C++ 입문에서 프로젝트까지"
series_order: 2
---

# 📘 Part 02. 기본 문법 (변수와 자료형, 연산자)

1. 개념 설명 (Concept)
변수란?
프로그램에서 데이터를 저장하는 공간
이름(식별자)을 붙여 사용
예: int age = 20;

자료형(Data Type)
정수(int): 10, -5
실수(float, double): 3.14, -0.01
문자(char): 'A', 'b'
문자열(string): "Hello"
논리(bool): true, false

연산자(Operator)
산술 연산자: +, -, *, /, %
관계 연산자: ==, !=, <, >
논리 연산자: &&, ||, !
대입 연산자: =, +=, -=

2. 그림 (Visual)
변수와 메모리 관계
int age = 20;
변수는 메모리 공간에 이름표를 붙여 관리하는 것과 같다.

3. 코드 예제 (Code Example)
#include <iostream>
using namespace std;

int main() {
    int a = 10;       // 정수형 변수
    double pi = 3.14; // 실수형 변수
    char ch = 'A';    // 문자
    bool flag = true; // 논리형

    cout << "정수: " << a << endl;
    cout << "실수: " << pi << endl;
    cout << "문자: " << ch << endl;
    cout << "논리: " << flag << endl;

    // 산술 연산
    int x = 7, y = 3;
    cout << "x + y = " << x + y << endl;
    cout << "x % y = " << x % y << endl;

    return 0;
}

4. 실행 결과 (Output)
정수: 10
실수: 3.14
문자: A
논리: 1
x + y = 10
x % y = 1
(참고: bool 값 true는 1, false는 0으로 출력됨)

5. 단계별 해설 (Step by Step)
int a = 10; → 메모리에 정수 10 저장
double pi = 3.14; → 실수 저장
char ch = 'A'; → 문자 저장 (작은따옴표 사용)
cout << flag; → true → 1로 출력
x + y, x % y → 연산 결과 출력

6. 응용 실습 (Practice Mission)
💡 미션 1: 계산기 만들기
두 정수를 입력받아 합, 차, 곱, 나눗셈을 출력하는 프로그램 작성
#include <iostream>
using namespace std;

int main() {
    int a, b;
    cout << "두 정수를 입력하세요: ";
    cin >> a >> b;

    cout << "합: " << a + b << endl;
    cout << "차: " << a - b << endl;
    cout << "곱: " << a * b << endl;
    cout << "몫: " << a / b << endl;

    return 0;
}

실행 예시
두 정수를 입력하세요: 10 3
합: 13
차: 7
곱: 30
몫: 3

💡 미션 2 (확장): BMI 계산기
키(cm)와 몸무게(kg)를 입력받아 BMI 지수를 출력
공식: BMI = 몸무게(kg) / (키(m) × 키(m))

실행 예시
키(cm): 170
몸무게(kg): 65
BMI = 22.4913

7. 요약 (Summary)
변수는 데이터를 저장하는 이름표이다.
자료형: 정수(int), 실수(double), 문자(char), 문자열(string), 논리(bool)
연산자: 산술, 관계, 논리, 대입 등 다양하게 제공된다.
cin으로 사용자 입력을 받을 수 있다.
계산기, BMI 프로그램을 작성하면서 변수·연산자 개념을 실제로 익혔다.
### 🔗 연결된 지식 네트워크
- [[📘 Part 01. C++ 시작하기]]: 동일한 C++ 입문 시리즈의 이전 파트로, Hello World와 기본 입출력 흐름을 이어서 다룸
- [[📘 Part 03. 조건문과 반복문 (제어문)]]: 동일 시리즈의 이전 파트로 변수, 자료형, 연산자 학습을 이어 제어문을 다룸
- [[📘 Part 05. 배열, 포인터, 참조]]: 동일 시리즈의 이전 파트로 C++ 변수와 자료형 개념을 다루며 본 문서의 배열·포인터 기초와 직접 연관된다.
- [[📘 Part 04. 클래스와 객체 지향 기초]]: 같은 C++ 입문 시리즈의 이전 파트
