---
url: "https://wikidocs.net/300285"
collected_at: "2026-06-14 05:24:09"
updated_at: "2026-06-14 05:25:41"
category: "AI/Software Engineering"
tags: [C++, 클래스, 객체, OOP, 캡슐화, 상속, 다형성]
summary: "C++에서 클래스(Class)는 객체(Object)를 만들기 위한 설계도로, 객체는 클래스로부터 생성된 실제 인스턴스이다. 주요 OOP 특징으로 캡슐화, 상속, 다형성을 소개하며, Car 클래스를 예로 멤버 변수(brand, speed)와 멤버 함수(drive())를 정의하고 객체 생성·사용 방법을 보여준다. Student 클래스와 BankAccount 클래스(생성자, deposit/withdraw 메서드, private balance) 실습 예제를 통해 객체 지향 개념을 단계별로 학습할 수 있다. 실행 결과와 해설을 제공하며, 다음 장으로 배열·포인터·참조를 안내한다."
source_title: "📘 Part 04. 클래스와 객체 지향 기초"
series: "c-입문에서-프로젝트까지-wikidocs"
series_title: "C++ 입문에서 프로젝트까지"
series_order: 4
---

# 📘 Part 04. 클래스와 객체 지향 기초

1. 개념 설명 (Concept)
클래스(Class)와 객체(Object)

클래스: 객체를 만들기 위한 설계도
객체: 클래스라는 설계도로 만들어진 실제 사물(인스턴스)
예: 자동차 클래스 → 특정 자동차(현대, 테슬라)는 객체

주요 특징

캡슐화(Encapsulation): 데이터와 기능을 하나로 묶음
상속(Inheritance): 기존 클래스 기능을 물려받아 확장
다형성(Polymorphism): 같은 이름의 함수가 다른 동작 수행

2. 그림 (Visual)
클래스와 객체 관계
클래스는 설계도이고, 객체는 그 설계도로 만들어진 구체적 실체이다.

3. 코드 예제 (Code Example)
간단한 클래스 정의
#include <iostream>
using namespace std;

class Car {
public:
    string brand;
    int speed;

    void drive() {
        cout << brand << " 자동차가 " << speed << "km/h로 달립니다." << endl;
    }
};

int main() {
    Car myCar;              // 객체 생성
    myCar.brand = "Hyundai";
    myCar.speed = 100;
    myCar.drive();          // 메서드 호출

    return 0;
}

4. 실행 결과 (Output)
Hyundai 자동차가 100km/h로 달립니다.

5. 단계별 해설 (Step by Step)

class Car { ... }; → Car라는 이름의 클래스 정의
string brand; int speed; → 멤버 변수 (객체 속성)
void drive() → 멤버 함수 (객체 동작)
Car myCar; → Car 클래스 기반으로 객체 생성
myCar.brand = "Hyundai"; → 객체의 속성 값 설정
myCar.drive(); → 객체의 메서드 실행

6. 응용 실습 (Practice Mission)
💡 미션 1: 학생 클래스 만들기
학생 이름과 점수를 저장하고, 점수를 출력하는 프로그램 작성

#include <iostream>
using namespace std;

class Student {
public:
    string name;
    int score;

    void printInfo() {
        cout << name << "의 점수: " << score << endl;
    }
};

int main() {
    Student s1;
    s1.name = "Minho";
    s1.score = 95;
    s1.printInfo();

    return 0;
}

실행 예시
Minho의 점수: 95

💡 미션 2 (확장): 은행 계좌 클래스
예금과 출금을 지원하는 BankAccount 클래스를 작성

#include <iostream>
using namespace std;

class BankAccount {
private:
    int balance;

public:
    BankAccount(int initial) {
        balance = initial;
    }

    void deposit(int amount) {
        balance += amount;
        cout << amount << "원 입금. 잔액: " << balance << endl;
    }

    void withdraw(int amount) {
        if (balance >= amount) {
            balance -= amount;
            cout << amount << "원 출금. 잔액: " << balance << endl;
        } else {
            cout << "잔액 부족!" << endl;
        }
    }
};

int main() {
    BankAccount myAcc(1000);
    myAcc.deposit(500);
    myAcc.withdraw(300);
    myAcc.withdraw(1500);

    return 0;
}

실행 예시
500원 입금. 잔액: 1500
300원 출금. 잔액: 1200
잔액 부족!

7. 요약 (Summary)

클래스는 객체를 만들기 위한 설계도이고, 객체는 그 설계도로 만든 실체이다.
클래스는 속성(멤버 변수)과 동작(멤버 함수)을 포함한다.
객체를 통해 데이터를 관리하고 기능을 실행할 수 있다.
실습: 학생 클래스, 은행 계좌 클래스를 구현하며 객체 지향 개념을 익힘.

👉 다음 장에서는 배열, 포인터, 참조를 배우며, 메모리와 변수의 관계를 더 깊게 이해한다.
### 🔗 연결된 지식 네트워크
- [[📘 Part 01. C++ 시작하기]]: 같은 C++ 입문 시리즈의 이전 파트
- [[📘 Part 02. 기본 문법 (변수와 자료형, 연산자)]]: 같은 C++ 입문 시리즈의 이전 파트
- [[📘 Part 03. 조건문과 반복문 (제어문)]]: 같은 C++ 입문 시리즈의 직전 파트
- [[📘 Part 05. 배열, 포인터, 참조]]: 같은 C++ 입문 시리즈의 다음 파트
