import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: TutorScreen(),
    );
  }
}

class TutorScreen extends StatefulWidget {
  @override
  _TutorScreenState createState() => _TutorScreenState();
}

class _TutorScreenState extends State<TutorScreen> {
  final TextEditingController _controller = TextEditingController();
  String _response = '';

  Future<void> _sendInput(String input) async {
    final response = await http.post(
      Uri.parse('http://yourbackendurl/tutor/process_response/'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'input': input}),
    );
    final responseData = json.decode(response.body);
    setState(() {
      _response = responseData['response'];
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('STEM Tutor')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(
              controller: _controller,
              decoration: InputDecoration(labelText: 'Enter your question'),
            ),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: () => _sendInput(_controller.text),
              child: Text('Submit'),
            ),
            SizedBox(height: 20),
            Text(_response),
          ],
        ),
      ),
    );
  }
}
