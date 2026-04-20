"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { ThemeSupa } from "@supabase/auth-ui-shared";
import { supabase } from "../supabaseClient";

const Auth = dynamic(() => import("@supabase/auth-ui-react").then((mod) => mod.Auth), { ssr: false });

export default function AuthPage() {
  const router = useRouter();

  useEffect(() => {
    
    // Listen for auth events
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (session) {
        // Once logged in, redirect to the dashboard
        router.push("/");
      }
    });
    return () => subscription.unsubscribe();
  }, [router]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'var(--bg-primary)' }}>
      <div style={{ width: '100%', maxWidth: '400px', padding: '2rem', background: 'var(--bg-secondary)', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
        <h1 style={{ textAlign: 'center', marginBottom: '2rem', color: 'var(--text-primary)' }}>☁️ Stego-Cloud</h1>
        <Auth
          supabaseClient={supabase}
          appearance={{ theme: ThemeSupa }}
          providers={['google']}
          theme="dark"
        />
      </div>
    </div>
  );
}
