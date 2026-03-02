from django.http import HttpResponse


def index(request):
    return HttpResponse(
        """
        <h1>Exam Engine Backend</h1>
        <p>Backend запущен.</p>
        <ul>
          <li><a href='/admin/'>/admin/</a> - админка</li>
          <li><a href='/api/exams/'>/api/exams/</a> - API экзаменов</li>
          <li><a href='http://127.0.0.1:5173/'>http://127.0.0.1:5173/</a> - frontend (Vite)</li>
        </ul>
        """
    )
