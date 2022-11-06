def log_upload(connection, request, person):
    data = request.POST
    adif = request.FILES['logfile'].read().decode(encoding='UTF-8', errors='backslashreplace')

    with connection.cursor() as cursor:
        cursor.execute("insert into upload (person, call, operator, contest) values (%s, %s, %s, %s) returning id", [person, data.get('call'), data.get('operator'), adif])
        upload_id = cursor.fetchone()
    connection.commit()

    return upload_id

