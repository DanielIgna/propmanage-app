import React, { useCallback, useRef, useState } from "react";
import { DSButton } from "../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../components/ui/dialog";

// Confirmare în stilul aplicației (în locul window.confirm).
// const [confirm, confirmDialog] = useConfirm();
// if (!(await confirm({ title, description, confirmLabel, danger }))) return;
// ...și randează {confirmDialog} în pagină.
export function useConfirm() {
  const [opts, setOpts] = useState(null);
  const resolver = useRef(null);

  const confirm = useCallback(
    (o) =>
      new Promise((resolve) => {
        resolver.current = resolve;
        setOpts(o);
      }),
    []
  );

  const close = (value) => {
    resolver.current?.(value);
    resolver.current = null;
    setOpts(null);
  };

  const dialog = (
    <Dialog open={!!opts} onOpenChange={(open) => !open && close(false)}>
      <DialogContent data-testid="radacini-confirm-dialog">
        <DialogHeader>
          <DialogTitle>{opts?.title}</DialogTitle>
          {opts?.description && <DialogDescription>{opts.description}</DialogDescription>}
        </DialogHeader>
        <DialogFooter>
          <DSButton variant="secondary" onClick={() => close(false)} data-testid="radacini-confirm-cancel">
            Renunță
          </DSButton>
          <DSButton variant={opts?.danger ? "danger" : "primary"} onClick={() => close(true)} data-testid="radacini-confirm-ok">
            {opts?.confirmLabel || "Confirmă"}
          </DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );

  return [confirm, dialog];
}
