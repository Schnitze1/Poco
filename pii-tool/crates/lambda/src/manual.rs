//! User-selected redactions, applied before mappings and the archive are stored.
use std::collections::{HashMap, HashSet};

use poco_core::vault::{EncodedOutput, TokenMapping};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct ManualMapping {
    token: String,
    value: String,
}

fn valid_token(token: &str) -> bool {
    let Some((class, number)) = token.rsplit_once('_') else { return false };
    class.starts_with(|c: char| c.is_ascii_alphabetic())
        && class.chars().all(|c| c.is_ascii_alphanumeric() || c == '_')
        && number.parse::<u32>().is_ok_and(|n| n > 0)
}

fn word_char(c: char) -> bool { c.is_alphanumeric() || c == '_' }

/// Transform real tokens atomically, or replace complete literal values outside tokens.
fn transform(text: &str, replacements: &HashMap<String, String>, rules: &[&ManualMapping]) -> String {
    let mut out = String::with_capacity(text.len());
    let mut i = 0;
    while i < text.len() {
        let rest = &text[i..];
        if rest.starts_with('[') {
            if let Some(end) = rest.find(']') {
                let token = &rest[1..end];
                if valid_token(token) {
                    out.push('[');
                    out.push_str(replacements.get(token).map(String::as_str).unwrap_or(token));
                    out.push(']');
                    i += end + 1;
                    continue;
                }
            }
        }
        let rule = rules.iter().find(|rule| {
            rest.starts_with(&rule.value)
                && !(rule.value.chars().next().is_some_and(word_char)
                    && text[..i].chars().next_back().is_some_and(word_char))
                && !(rule.value.chars().next_back().is_some_and(word_char)
                    && rest[rule.value.len()..].chars().next().is_some_and(word_char))
        });
        if let Some(rule) = rule {
            out.push_str(&format!("[{}]", rule.token));
            i += rule.value.len();
        } else {
            let ch = rest.chars().next().unwrap();
            out.push(ch);
            i += ch.len_utf8();
        }
    }
    out
}

pub fn apply(encoded: &mut EncodedOutput, source: &str, rules: &[ManualMapping]) -> Result<(), String> {
    let mut tokens = HashSet::new();
    let mut values = HashSet::new();
    if rules.len() > 1000 { return Err("too many manual mappings".into()); }
    for rule in rules {
        if !valid_token(&rule.token) || rule.token.len() > 128 || rule.value.trim().is_empty()
            || !tokens.insert(rule.token.clone()) || !values.insert(rule.value.clone()) {
            return Err("manual mappings require unique tokens and nonempty, unique values".into());
        }
    }
    let reserved_manual = tokens.clone();
    tokens.extend(encoded.mappings.iter().map(|m| m.class.clone()));
    let mut renamed = HashMap::new();
    for mapping in &mut encoded.mappings {
        let next = if let Some(rule) = rules.iter().find(|rule| rule.value == mapping.value) {
            rule.token.clone()
        } else if reserved_manual.contains(&mapping.class) {
            let class = mapping.class.rsplit_once('_').map(|(class, _)| class).unwrap_or("Custom");
            let mut n = 1;
            while tokens.contains(&format!("{class}_{n}")) { n += 1; }
            format!("{class}_{n}")
        } else { mapping.class.clone() };
        tokens.insert(next.clone());
        renamed.insert(mapping.class.clone(), next.clone());
        mapping.class = next.clone();
        mapping.token = next;
    }
    let mut ordered: Vec<_> = rules.iter().collect();
    ordered.sort_by_key(|rule| std::cmp::Reverse(rule.value.len()));
    encoded.redacted_text = transform(&encoded.redacted_text, &renamed, &ordered);
    for rule in rules {
        encoded.mappings.retain(|m| m.class != rule.token);
        encoded.mappings.push(TokenMapping {
            token: rule.token.clone(), class: rule.token.clone(), value: rule.value.clone(),
            first_offset: source.find(&rule.value).unwrap_or(0),
        });
    }
    encoded.mappings.sort_by(|a, b| (a.first_offset, &a.class).cmp(&(b.first_offset, &b.class)));
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rule(token: &str, value: &str) -> ManualMapping {
        ManualMapping { token: token.into(), value: value.into() }
    }

    #[test]
    fn manual_values_preserve_words_tokens_and_unicode() {
        let mut encoded = EncodedOutput {
            redacted_text: "Ann Annual, Ann Lee; Zoë. [Email_1]".into(), mappings: vec![],
        };
        let source = encoded.redacted_text.clone();
        apply(&mut encoded, &source, &[rule("Name_1", "Ann"), rule("Name_2", "Ann Lee"),
            rule("Name_3", "Zoë"), rule("Custom_1", "Email")]).unwrap();
        assert_eq!(encoded.redacted_text, "[Name_1] Annual, [Name_2]; [Name_3]. [Email_1]");
    }

    #[test]
    fn automatic_and_manual_tokens_do_not_collide_or_cascade() {
        let mut encoded = EncodedOutput { redacted_text: "[Email_1] [Email_2]".into(), mappings: vec![
            TokenMapping { token: "Email_1".into(), class: "Email_1".into(), value: "a@example.com".into(), first_offset: 0 },
            TokenMapping { token: "Email_2".into(), class: "Email_2".into(), value: "b@example.com".into(), first_offset: 14 },
        ] };
        apply(&mut encoded, "a@example.com b@example.com", &[rule("Email_1", "b@example.com")]).unwrap();
        assert_eq!(encoded.redacted_text, "[Email_3] [Email_1]");
        assert_eq!(encoded.mappings.len(), 2);
        assert_eq!(encoded.mappings.iter().find(|m| m.class == "Email_1").unwrap().value, "b@example.com");
    }

    #[test]
    fn invalid_manual_rules_are_rejected() {
        for rules in [vec![rule("Custom_1", " ")], vec![rule("bad token", "secret")],
            vec![rule("Custom_1", "secret"), rule("Custom_1", "other")]] {
            let mut encoded = EncodedOutput { redacted_text: "secret".into(), mappings: vec![] };
            assert!(apply(&mut encoded, "secret", &rules).is_err());
        }
    }
}
