//! User-selected redactions, applied before mappings and the archive are stored.
use std::collections::{HashMap, HashSet};

use poco_core::vault::{EncodedOutput, TokenMapping};
use serde::Deserialize;

#[cfg(test)]
#[path = "manual_tests.rs"]
mod tests;

#[derive(Debug, Deserialize)]
pub struct ManualMapping {
    token: String,
    value: String,
    #[serde(rename = "sourceValue")]
    source_value: Option<String>,
}

impl ManualMapping {
    fn source(&self) -> &str {
        self.source_value.as_deref().unwrap_or(&self.value)
    }
}

fn valid_token(token: &str) -> bool {
    let Some((class, number)) = token.rsplit_once('_') else { return false };
    class.starts_with(|c: char| c.is_ascii_alphabetic())
        && class.chars().all(|c| c.is_ascii_alphanumeric() || c == '_')
        && number.chars().all(|c| c.is_ascii_digit())
        && number.parse::<u32>().is_ok_and(|n| n > 0)
}

fn word_char(c: char) -> bool { c.is_alphanumeric() || c == '_' }

/// Transform real tokens atomically, or replace complete literal values outside tokens.
fn transform(text: &str, replacements: &HashMap<String, String>, rules: &[&ManualMapping]) -> String {
    let capacity = text.len();
    let mut out = String::with_capacity(capacity);
    let mut i = 0;
    while i < text.len() {
        let rest = &text[i..];
        if rest.starts_with('[') {
            if let Some(end) = rest.find(']') {
                let token = &rest[1..end];
                if valid_token(token) {
                    out.push('[');
                    let replacement = replacements.get(token).map(String::as_str).unwrap_or(token);
                    out.push_str(replacement);
                    out.push(']');
                    i += end + 1;
                    continue;
                }
            }
        }
        let rule = rules.iter().find(|rule| {
            let literal = rule.source();
            rest.starts_with(literal)
                && !(literal.chars().next().is_some_and(word_char)
                    && text[..i].chars().next_back().is_some_and(word_char))
                && !(literal.chars().next_back().is_some_and(word_char)
                    && rest[literal.len()..].chars().next().is_some_and(word_char))
        });
        if let Some(rule) = rule {
            out.push_str(&format!("[{}]", rule.token));
            i += rule.source().len();
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
        let token = rule.token.clone();
        let value = rule.source().to_string();
        if !valid_token(&rule.token) || rule.token.len() > 128 || rule.value.trim().is_empty() || rule.source().trim().is_empty()
            || !tokens.insert(token) || !values.insert(value) {
            return Err("manual mappings require unique tokens and nonempty, unique values".into());
        }
    }
    let reserved_manual = tokens.clone();
    let automatic_tokens: Vec<_> = encoded.mappings.iter().map(|m| m.class.clone()).collect();
    tokens.extend(automatic_tokens);
    let mut renamed = HashMap::new();
    for mapping in &mut encoded.mappings {
        let next = if let Some(rule) = rules.iter().find(|rule| rule.source() == mapping.value) {
            rule.token.clone()
        } else if reserved_manual.contains(&mapping.class) {
            let class = mapping.class.rsplit_once('_').map(|(class, _)| class).unwrap_or("Custom");
            let mut n = 1;
            while tokens.contains(&format!("{class}_{n}")) { n += 1; }
            format!("{class}_{n}")
        } else { mapping.class.clone() };
        let reserved = next.clone();
        tokens.insert(reserved);
        let old_token = mapping.class.clone();
        let new_token = next.clone();
        renamed.insert(old_token, new_token);
        mapping.class = next.clone();
        mapping.token = next;
    }
    let mut ordered: Vec<_> = rules.iter().collect();
    ordered.sort_by_key(|rule| std::cmp::Reverse(rule.source().len()));
    encoded.redacted_text = transform(&encoded.redacted_text, &renamed, &ordered);
    for rule in rules {
        encoded.mappings.retain(|m| m.class != rule.token);
        let literal = rule.source();
        encoded.mappings.push(TokenMapping {
            token: rule.token.clone(), class: rule.token.clone(), value: rule.value.clone(),
            first_offset: source.find(literal).unwrap_or(0),
        });
    }
    encoded.mappings.sort_by(|a, b| (a.first_offset, &a.class).cmp(&(b.first_offset, &b.class)));
    Ok(())
}
