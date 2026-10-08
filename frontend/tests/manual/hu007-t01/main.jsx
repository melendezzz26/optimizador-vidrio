import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import CustomPieceEditor from "../../../src/features/orders/CustomPieceEditor";
import "./manual-test.css";

// Standalone manual test entry; not imported by the application.
createRoot(document.getElementById("manual-test-root")).render(
  <StrictMode>
    <CustomPieceEditor />
  </StrictMode>,
);
