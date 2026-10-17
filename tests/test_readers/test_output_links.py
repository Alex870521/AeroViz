"""After a read, the files it wrote are listed as clickable `file://` links."""
import os
import time

from AeroViz.rawDataReader.core.output_links import print_output_files


def test_lists_only_files_written_this_run(tmp_path, capsys):
    folder = tmp_path / 'a b' / '中文'          # spaces and CJK, as on the shared drive
    folder.mkdir(parents=True)
    old = folder / 'old.csv'
    old.write_text('x')
    os.utime(old, (time.time() - 3600, time.time() - 3600))
    started = time.time()
    (folder / 'output test.csv').write_text('y')

    written = print_output_files(folder, since=started)

    assert [p.name for p in written] == ['output test.csv']
    out = capsys.readouterr().out
    assert 'output test.csv' in out and 'old.csv' not in out


def test_links_are_emitted_on_a_terminal(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv('FORCE_COLOR', '1')
    (tmp_path / 'a b.csv').write_text('y')
    print_output_files(tmp_path, since=time.time() - 60)
    out = capsys.readouterr().out
    assert '\x1b]8;' in out                       # OSC 8 hyperlink
    assert (tmp_path / 'a b.csv').resolve().as_uri() in out


def test_apple_terminal_gets_an_open_command(tmp_path, capsys, monkeypatch):
    """Terminal.app cannot click either kind of link; give it a command to paste."""
    monkeypatch.setenv('TERM_PROGRAM', 'Apple_Terminal')
    folder = tmp_path / 'a b'
    folder.mkdir()
    (folder / 'x.csv').write_text('y')
    print_output_files(folder, since=time.time() - 60)
    out = capsys.readouterr().out
    assert f"open '{folder}'" in out
    assert 'click to open' not in out
