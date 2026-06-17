---
url: "https://wikidocs.net/272028"
collected_at: "2026-06-14 08:34:22"
updated_at: "2026-06-14 08:34:44"
category: "AI/Software Engineering"
tags: [Rust, bool, 스칼라 타입, 데이터 타입, 기초 문법]
summary: "Rust의 bool 타입은 true 또는 false 값을 저장하며 주로 if 조건문 등에서 사용된다. let t1 = true;와 같이 타입 추론으로 선언하거나 let t2: bool = false;처럼 명시적으로 타입을 지정할 수 있다. bool 값은 조건식에 직접 사용 가능하며, Copy 트레이트가 적용되어 소유권 이동 없이 복사된다. 이 문서는 Rust 스칼라 타입 중 부울 타입의 기본 사용법과 간단한 코드 예제를 제공한다."
source_title: "C. 부울"
series: "러스트-기초부터-고급까지-wikidocs"
series_title: "러스트 기초부터 고급까지"
series_order: 11
document_type: "tutorial"
---

# C. 부울

bool 타입은 true 혹은 false 값을 가진다. if 같은 조건문에 주로 사용된다.
let t1 = true;
let t2:bool = false;

if t1 {
  ...
}
### 🔗 연결된 지식 네트워크
- [[3.1 메인 함수와 화면 출력]]: 같은 Rust 튜토리얼 시리즈의 기본 문법 섹션으로 데이터 타입과 연계됨
- [[03. 초급: Rust 기본 문법]]: 부모 챕터로 bool 타입이 포함된 데이터 타입 섹션의 상위 문서
- [[D. 문자]]: 동일한 Rust 스칼라 타입 시리즈의 이전 문서로 bool 타입을 다룸
- [[3.3.2 복합 타입]]: 동일 시리즈 3.3.1 하위 항목으로 데이터 타입 학습 흐름 연결
- [[A. 튜플]]: 동일한 3.3.1 스칼라 타입 섹션의 형제 문서
