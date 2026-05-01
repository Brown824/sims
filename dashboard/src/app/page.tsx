import { createClient } from '@/utils/supabase/server'
import { cookies } from 'next/headers'

export default async function Page() {
  const cookieStore = await cookies()
  const supabase = createClient(cookieStore)

  const { data: todos } = await supabase.from('todos').select()

  return (
    <div className="min-h-screen bg-slate-900 text-white p-8">
      <h1 className="text-4xl font-bold mb-8 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">
        SIMS Dashboard
      </h1>
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl">
        <h2 className="text-xl font-semibold mb-4 text-slate-300">Live Feedback (Todos Mock)</h2>
        <ul className="space-y-3">
          {todos?.map((todo) => (
            <li key={todo.id} className="p-4 bg-slate-700 rounded-lg border border-slate-600 hover:border-blue-500 transition-colors">
              {todo.name}
            </li>
          ))}
          {(!todos || todos.length === 0) && (
            <p className="text-slate-500 italic">No data found in 'todos' table.</p>
          )}
        </ul>
      </div>
    </div>
  )
}
