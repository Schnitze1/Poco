use super::*;

fn rule(token: &str, value: &str, source: Option<&str>) -> ManualMapping {
    ManualMapping {
        token: token.into(),
        value: value.into(),
        source_value: source.map(str::to_string),
    }
}

fn encoded(text: &str) -> EncodedOutput {
    EncodedOutput {
        redacted_text: text.into(),
        mappings: vec![],
    }
}

#[test]
fn rejects_invalid_and_duplicate_manual_rules_without_changing_output() {
    let cases = vec![
        vec![rule("missing_number", "secret", None)],
        vec![rule("Custom_0", "secret", None)],
        vec![rule("1Custom_1", "secret", None)],
        vec![rule("Custom-Name_1", "secret", None)],
        vec![rule("Custom_1", " ", None)],
        vec![rule("Custom_1", "secret", Some(" "))],
        vec![rule(&format!("{}_1", "A".repeat(129)), "secret", None)],
        vec![rule("Custom_1", "one", None), rule("Custom_1", "two", None)],
        vec![
            rule("Custom_1", "same", None),
            rule("Custom_2", "same", None),
        ],
    ];
    for rules in cases {
        let mut output = encoded("original text");
        assert!(apply(&mut output, "original text", &rules).is_err());
        assert_eq!(output.redacted_text, "original text");
        assert!(output.mappings.is_empty());
    }
}

#[test]
fn rejects_more_than_one_thousand_rules() {
    let rules: Vec<_> = (1..=1001)
        .map(|i| rule(&format!("Custom_{i}"), &format!("value-{i}"), None))
        .collect();
    assert_eq!(
        apply(&mut encoded("text"), "text", &rules).unwrap_err(),
        "too many manual mappings"
    );
}

#[test]
fn applies_longest_literals_at_unicode_word_boundaries_and_preserves_existing_tokens() {
    let source = "Ann Lee met Ann and Annette, _Ann Ann_. 李雷 met 李雷明. [Custom_9] [unfinished";
    let mut output = encoded(source);
    apply(
        &mut output,
        source,
        &[
            rule("Name_1", "Ann", None),
            rule("Name_2", "Ann Lee", None),
            rule("Name_3", "李雷", None),
        ],
    )
    .unwrap();
    assert_eq!(
        output.redacted_text,
        "[Name_2] met [Name_1] and Annette, _Ann Ann_. [Name_3] met 李雷明. [Custom_9] [unfinished"
    );
    assert_eq!(
        output
            .mappings
            .iter()
            .find(|m| m.class == "Name_2")
            .unwrap()
            .first_offset,
        0
    );
    assert_eq!(output.mappings.len(), 3);
}

#[test]
fn reserves_manual_tokens_without_overwriting_automatic_mappings() {
    let source = "secret first@example.com second@example.com Alice";
    let mut output = encoded("secret [Email_1] [Email_2] Alice");
    output.mappings = vec![
        TokenMapping {
            token: "Email_1".into(),
            class: "Email_1".into(),
            value: "first@example.com".into(),
            first_offset: 7,
        },
        TokenMapping {
            token: "Email_2".into(),
            class: "Email_2".into(),
            value: "second@example.com".into(),
            first_offset: 25,
        },
    ];
    apply(
        &mut output,
        source,
        &[
            rule("Email_1", "secret", None),
            rule("Name_1", "Alice", None),
        ],
    )
    .unwrap();
    assert_eq!(
        output.redacted_text,
        "[Email_1] [Email_3] [Email_2] [Name_1]"
    );
    assert!(output
        .mappings
        .iter()
        .any(|m| m.class == "Email_3" && m.value == "first@example.com"));
    assert!(output
        .mappings
        .iter()
        .any(|m| m.class == "Email_1" && m.value == "secret"));
}

#[test]
fn manual_override_of_detected_value_updates_the_token_and_retains_corrected_value() {
    let mut output = encoded("Hello [Name_1]");
    output.mappings.push(TokenMapping {
        token: "Name_1".into(),
        class: "Name_1".into(),
        value: "Alice".into(),
        first_offset: 6,
    });
    apply(
        &mut output,
        "Hello Alice",
        &[rule("Custom_1", "Corrected Alice", Some("Alice"))],
    )
    .unwrap();
    assert_eq!(output.redacted_text, "Hello [Custom_1]");
    assert_eq!(output.mappings.len(), 1);
    assert_eq!(output.mappings[0].value, "Corrected Alice");
    assert_eq!(output.mappings[0].first_offset, 6);
}
