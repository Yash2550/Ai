import os
content = open('templates/index.html', 'r', encoding='utf-8').read()

new_btn = '''
          <button id="digitizeReveOfficialBtn" class="btn-primary"
            style="display:flex; align-items:center; justify-content:center; gap:8px; padding:10px 15px; border-radius:6px; font-weight:600; cursor:pointer;">
            🚀 Digitize with Official REVE API
          </button>
'''
if 'digitizeReveOfficialBtn' not in content:
    content = content.replace('<!-- Canva Studio Launch Button -->', '<!-- Canva Studio Launch Button -->\n' + new_btn)

new_js = '''
      const digitizeReveOfficialBtn = document.getElementById('digitizeReveOfficialBtn');
      if (digitizeReveOfficialBtn) {
        digitizeReveOfficialBtn.addEventListener('click', async function () {
          if (!currentResultImageSrc) {
            alert('No image to digitize!');
            return;
          }
          
          const originalBtnText = digitizeReveOfficialBtn.innerHTML;
          digitizeReveOfficialBtn.innerHTML = '⏳ Processing with REVE AI...';
          digitizeReveOfficialBtn.disabled = true;

          try {
            const formData = new FormData();
            
            // Convert data URI to Blob
            const response = await fetch(currentResultImageSrc);
            const blob = await response.blob();
            formData.append('image', blob, 'label.png');

            const res = await fetch('/api/digitize-reve', {
              method: 'POST',
              body: formData
            });

            const data = await res.json();
            
            if (res.ok && data.fabric_json) {
                // Initialize canvas if needed
                if (!fabricReves) {
                  fabricReves = new fabric.Canvas('reveStudioReves', { preserveObjectStacking: true });
                }
                
                // Load official JSON
                fabricReves.loadFromJSON(data.fabric_json, function() {
                  fabricReves.renderAll();
                  reveStudioModal.style.display = 'flex';
                });
            } else {
              alert('Reve API Failed: ' + (data.error || 'Unknown error'));
            }
          } catch (err) {
            console.error(err);
            alert('An error occurred during official REVE digitization.');
          } finally {
            digitizeReveOfficialBtn.innerHTML = originalBtnText;
            digitizeReveOfficialBtn.disabled = false;
          }
        });
      }
'''
if 'digitizeReveOfficialBtn.addEventListener' not in content:
    content = content.replace('// Close Modal Logic', new_js + '\n      // Close Modal Logic')
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated index.html')
else:
    print('Already updated')
