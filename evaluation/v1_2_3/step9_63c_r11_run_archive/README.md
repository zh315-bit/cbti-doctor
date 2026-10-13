# r11 正式执行证据归档（只读副本）

本目录是 r11 正式执行（事务 `txn-v3-e96bdfed431149098ea815dec817d6ab`）五个运行产物的逐字节副本。原件仍在被 git 忽略的 `evaluation/v4_runs/` 下，未被修改。

- `run_root/` 保持原件相对 `evaluation/v4_runs/` 的路径；目录名故意不叫 `v4_runs`，所有扫描 attempt 与命名空间的代码都只以 `evaluation/v4_runs` 为根，不会把这些副本当成新的 attempt。
- `MANIFEST.json`：源路径、归档路径、字节数、SHA-256、源文件修改时间、复制时间与当时的 HEAD。
- `SHA256SUMS`：在本目录下运行 `shasum -a 256 -c SHA256SUMS` 校验。

**不得修改本目录下的任何文件。** 生命周期状态的已知缺陷见 `../step9_63c_r11_known_limitations.md`（KL-1）。
