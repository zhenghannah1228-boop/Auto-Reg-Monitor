-- scan_runs: 允许匿名写入(日扫集写日志)
CREATE POLICY scan_runs_insert ON scan_runs FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY scan_runs_update ON scan_runs FOR UPDATE TO anon USING (true) WITH CHECK (true);

-- scan_matrix: 允许匿名更新(日扫集更新扫集格)
CREATE POLICY scan_matrix_insert ON scan_matrix FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY scan_matrix_update ON scan_matrix FOR UPDATE TO anon USING (true) WITH CHECK (true);
