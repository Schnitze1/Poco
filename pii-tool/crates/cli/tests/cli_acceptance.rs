use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

struct Workspace(PathBuf);

impl Workspace {
    fn new() -> Self {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path =
            std::env::temp_dir().join(format!("poco-cli-test-{}-{nonce}", std::process::id()));
        std::fs::create_dir_all(&path).unwrap();
        Self(path)
    }

    fn run(&self, input: &str) -> (String, String) {
        let mut child = Command::new(env!("CARGO_BIN_EXE_pii-cli"))
            .current_dir(&self.0)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        child
            .stdin
            .take()
            .unwrap()
            .write_all(input.as_bytes())
            .unwrap();
        let output = child.wait_with_output().unwrap();
        assert!(output.status.success(), "CLI failed: {:?}", output);
        (
            String::from_utf8(output.stdout).unwrap(),
            String::from_utf8(output.stderr).unwrap(),
        )
    }
}

impl Drop for Workspace {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

#[test]
fn interactive_session_encodes_decodes_updates_mappings_and_clears() {
    let workspace = Workspace::new();
    let input = "3\ninvalid\n1\n2\nContact cli@example.com\n;;\n1\n2\ncli@example.com\n;;\n3\n2\n2\nReach [Email_1] [Person_99]\n;;\n4\n3\n5\n";
    let (stdout, stderr) = workspace.run(input);
    assert!(stderr.is_empty(), "{stderr}");
    assert!(stdout.contains("Invalid input."));
    assert!(stdout.contains("No mappings in current session."));
    assert!(stdout.contains("[Email_1]"));
    assert!(stdout.contains("Reach cli@example.com [Person_99]"));
    assert!(stdout.contains("Hallucinated tokens detected"));
    assert!(stdout.contains("Session cleared."));
    let saved = std::fs::read_to_string(workspace.0.join("output/redacted.txt")).unwrap();
    assert!(saved.contains("[Email_1]"));
    assert!(!saved.contains("cli@example.com"));
}

#[test]
fn text_file_input_and_plain_text_are_supported() {
    let workspace = Workspace::new();
    let file = workspace.0.join("contact.txt");
    std::fs::write(&file, "Contact file@example.com").unwrap();
    let (stdout, stderr) =
        workspace.run(&format!("1\n1\n{}\n1\n2\nhello\n;;\n5\n", file.display()));
    assert!(stderr.is_empty(), "{stderr}");
    assert!(stdout.contains("file@example.com"));
    assert!(stdout.contains("No PII detected"));
    assert_eq!(
        std::fs::read_to_string(workspace.0.join("output/redacted.txt"))
            .unwrap()
            .trim(),
        "hello"
    );
}

#[test]
fn docx_file_input_uses_document_extraction() {
    let workspace = Workspace::new();
    let file =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../test_data/onboarding_dossier.docx");
    let (stdout, stderr) = workspace.run(&format!("1\n1\n{}\n5\n", file.display()));
    assert!(stderr.is_empty(), "{stderr}");
    assert!(stdout.contains("Extracting text..."));
    assert!(stdout.contains("Full redacted text written to"));
    assert!(
        std::fs::metadata(workspace.0.join("output/redacted.txt"))
            .unwrap()
            .len()
            > 0
    );
}

#[test]
fn submenu_validation_back_and_empty_inputs_return_to_menu() {
    let workspace = Workspace::new();
    let (stdout, stderr) = workspace.run("1\ninvalid\n1\nmissing.txt\n3\n1\n2\n;;\n2\n2\n;;\n5\n");
    assert!(stderr.is_empty(), "{stderr}");
    assert!(stdout.contains("Invalid input."));
    assert!(stdout.contains("File not found:"));
    assert_eq!(stdout.matches("No text provided.").count(), 2);
}

#[test]
fn unreadable_and_unsupported_files_report_errors_without_crashing() {
    let workspace = Workspace::new();
    std::fs::create_dir(workspace.0.join("directory.txt")).unwrap();
    std::fs::write(
        workspace.0.join("unsupported.bin"),
        b"not a supported document",
    )
    .unwrap();
    let (_, stderr) = workspace.run("1\n1\ndirectory.txt\n1\n1\nunsupported.bin\n5\n");
    assert!(stderr.contains("Error reading txt:"));
    assert!(stderr.contains("Error extracting text:"));
}

#[test]
fn output_directory_failure_is_reported() {
    let workspace = Workspace::new();
    std::fs::write(workspace.0.join("output"), "occupied path").unwrap();
    let (stdout, stderr) = workspace.run("1\n2\nContact a@example.com\n;;\n5\n");
    assert!(stdout.contains("[Email_1]"));
    assert!(stderr.contains("Failed to create output dir:"));
}

#[test]
fn output_file_failure_is_reported() {
    let workspace = Workspace::new();
    std::fs::create_dir_all(workspace.0.join("output/redacted.txt")).unwrap();
    let (_, stderr) = workspace.run("1\n2\nContact a@example.com\n;;\n5\n");
    assert!(stderr.contains("Failed to write output file:"));
}

#[test]
fn eof_at_main_menu_or_during_multiline_input_exits_cleanly() {
    let workspace = Workspace::new();
    for input in ["", "1\n2\nunfinished text\n", "1\n"] {
        let (stdout, stderr) = workspace.run(input);
        assert!(stderr.is_empty(), "{stderr}");
        assert!(stdout.contains("EOF detected. Exiting..."));
    }
}
