---
url: "https://wikidocs.net/272031"
collected_at: "2026-06-14 08:34:23"
updated_at: "2026-06-14 08:34:52"
category: "AI/Software Engineering"
tags: [Rust, char, 스칼라 타입, 데이터 타입, 기초 문법]
summary: "Rust의 문자 타입은 char이며, 알파벳 문자를 싱글 따옴표로 감싸서 선언한다. let a = 'a'; let z = 'z';와 같이 변수를 선언한 뒤 println! 매크로로 출력하는 간단한 예제가 제공된다. 본 문서는 3.3.1 스칼라 타입 섹션의 D. 문자 항목으로, Rust 기본 데이터 타입 학습의 일부이다."
source_title: "D. 문자"
series: "러스트-기초부터-고급까지-wikidocs"
series_title: "러스트 기초부터 고급까지"
series_order: 12
document_type: "tutorial"
---

# D. 문자

문자 타입은 char이다. 알파벳 문자를 싱글 따옴표로 감싸서 입력하면 된다.
let a = 'a';
let z = 'z';

println!("{}, {}", a, z);  // a, z
### 🔗 연결된 지식 네트워크
- [[C. 부울]]: 동일한 Rust 스칼라 타입 시리즈의 이전 문서로 bool 타입을 다룸
- [[3.3.2 복합 타입]]: 동일 시리즈 3.3.1 하위 항목으로 데이터 타입 학습 흐름 연결
- [[A. 튜플]]: 동일한 3.3.1 스칼라 타입 섹션의 형제 문서
