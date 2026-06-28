import { Routes, Route } from "react-router-dom";

import Home from "./assets/pages/home";
import Dashboard from "./assets/pages/dashboard";
import Signup from "./assets/pages/signup";
import Login from "./assets/pages/login";
import Profile from "./assets/pages/profile";
import PasswordReset from "./assets/pages/PasswordReset";
import NotFound from "./assets/pages/notfound";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/dashboard" element= {<Dashboard/>} /> 
      <Route path="/signup" element= {<Signup/>} />
      <Route path="/login" element= {<Login/>} />
      <Route path="/profile" element= {<Profile/>} />
      <Route path="/PasswordReset" element= {<PasswordReset/>} />
      <Route path="*" element={<NotFound />} />

    </Routes>
  );
}