import { useCallback, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";

export function SupabaseTestPage() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    if (!supabase) {
      setError("Lipsesc REACT_APP_SUPABASE_URL / REACT_APP_SUPABASE_PUBLISHABLE_KEY din frontend/.env");
      setLoading(false);
      return;
    }
    const { data, error } = await supabase
      .from("test_users")
      .select("id, name, email, role, created_at")
      .order("id");
    if (error) setError(error.message);
    else setRows(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-4">
          <CardTitle>Test Supabase — tabelul test_users</CardTitle>
          <Button size="sm" variant="outline" onClick={load} disabled={loading}>
            {loading ? "Se încarcă…" : "Reîncarcă"}
          </Button>
        </CardHeader>
        <CardContent>
          {error ? (
            <p className="text-sm text-red-500">Eroare: {error}</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Nume</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Rol</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell>{u.id}</TableCell>
                    <TableCell>{u.name}</TableCell>
                    <TableCell>{u.email}</TableCell>
                    <TableCell><Badge variant="secondary">{u.role}</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {!loading && !error && (
            <p className="mt-4 text-xs text-muted-foreground">
              {rows.length} rânduri citite direct din Supabase cu cheia publică.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
