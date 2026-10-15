import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="mx-auto max-w-md px-5 py-24 text-center">
      <div className="font-display text-7xl font-bold text-white/15">404</div>
      <h1 className="mt-2 font-display text-2xl font-bold">Lost in the hackathon?</h1>
      <p className="mt-2 text-sm text-white/50">That page doesn&apos;t exist. The good stuff is one click away.</p>
      <div className="mt-6 flex justify-center gap-3">
        <Link to="/" className="btn-primary text-sm">Home</Link>
        <Link to="/dashboard" className="btn-ghost text-sm">Dashboard</Link>
      </div>
    </div>
  )
}
