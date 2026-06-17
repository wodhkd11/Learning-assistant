---
url: "https://wikidocs.net/272032"
collected_at: "2026-06-14 08:34:24"
updated_at: "2026-06-14 08:35:30"
category: "AI/Software Engineering"
tags: [Rust, tuple, 복합 타입, 데이터 타입, 기초 문법]
summary: "Rust의 튜플(tuple)은 여러 개의 값을 괄호로 묶어 표현하는 복합 타입으로, 각 요소의 타입이 서로 달라도 된다. let p:(&str, u32) = (\"Lee\", 20);처럼 선언하며, p.0, p.1과 같은 인덱스 접근을 통해 개별 요소를 읽는다. 전체 내용을 출력할 때는 {:?} 포맷을 사용해야 하며, {}는 스칼라 타입에만 적용된다. 함수에서 튜플을 반환할 경우 반환값을 튜플 변수로 받아 .0, .1로 요소를 추출하는 방식으로 사용한다. 예제 코드에서는 get_info() 함수가 (i32, f64) 튜플을 반환하는 패턴을 보여준다."
source_title: "A. 튜플"
series: "러스트-기초부터-고급까지-wikidocs"
series_title: "러스트 기초부터 고급까지"
series_order: 14
document_type: "tutorial"
---

# A. 튜플

Rust에서 지원하는 편리한 데이터 타입이다. C에서는 이러한 데이터 타입이 없고, Java와 Python에는 유사한 타입이 있다.

튜플은 여러 데이터 타입을 괄호로 감싼 것이다. 괄호안의 타입은 서로 달라도 된다. let p:(&str, u32) = ("Lee", 20);
튜플의 원소로의 접근은 p.0 p.1과 같이 인덱스를 이용한다. println!("name:{}, age={}",p.0, p.1);

튜플의 내용 전체를 한 번에 출력하려면, {:?}를 사용해야 한다. println!("{:?}",p); 
Rust에서는 단일 값을 가지는 스칼라형 변수의 출력은 {}를 사용하고, 복합 타입은 {:?}를 사용해야 한다.

튜플의 값을 받을 때는 튜플로 받아야 한다. 예를 들어 get_info 함수라 (i32,f64) 형태의 튜플를 리턴한다면, 이것을 받는 변수는 튜플형태가 되고, 이 튜플의 원소를 빼낼 때는 해당 변수에 .0과 같이 마침표와 인덱스를 이용해서 원소를 빼낸다.

fn main(){
    let p:(&str, u32) = ("Lee", 20);
    println!("name:{}, age={}",p.0, p.1);  //name:Lee, age=20
    println!("{:?}",p);  //("Lee", 20)

    let info = get_info();
    println!("age:{}, height={}",info.0, info.1);  //age:20, height=60
}

fn get_info() -> (i32, f64){
    let age = 20;
    let height = 60.5;

    return (age,height);
}
### 🔗 연결된 지식 네트워크
- [[3.3.2 복합 타입]]: 튜플이 속한 상위 섹션으로, 복합 타입의 개념과 배열과의 관계를 설명
- [[D. 문자]]: 동일한 3.3.1 스칼라 타입 섹션의 형제 문서
- [[C. 부울]]: 동일한 3.3.1 스칼라 타입 섹션의 형제 문서
