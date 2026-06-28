// src/assets/pages/notfound.jsx
import { Link } from "react-router-dom";
export default function NotFound() {
  return (
    <div style={{padding: 32}}>
      <h1>404 — Page not found</h1>
      <p><Link to="/">Go Home</Link></p>
    </div>
  );
}
