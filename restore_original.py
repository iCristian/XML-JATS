#!/usr/bin/env python3
# Reconstruct original 4975.xml from conversation read outputs

original_lines = """1: <?xml version="1.0" encoding="UTF-8"?>
2: <!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.1 20151215//EN" "JATS-journalpublishing1.dtd">
3: <article xmlns:xlink="http://www.w3.org/1999/xlink" dtd-version="1.0" article-type="research-article" xml:lang="es" specific-use="sps-1.8">
4:     <front>
5:         <journal-meta>
6:             <journal-id journal-id-type="publisher-id">Revista</journal-id>
7:             <journal-title-group>
8:                 <journal-title>Revista Matronería Actual</journal-title>
9:                 <abbrev-journal-title abbrev-type="publisher">Rev. Matronería Act.</abbrev-journal-title>
10:             </journal-title-group>
11:             <issn pub-type="ppub">2452-5820</issn>
12:             <publisher>
13:                 <publisher-name>Universidad de Valparaíso</publisher-name>
14:             </publisher>
15:         </journal-meta>
16:         <article-meta>
17:             <article-id pub-id-type="doi">10.22370/revmat.1.2026.4975</article-id>
18:             <article-categories>
19:                 <subj-group subj-group-type="heading">
20:                     <subject>Original Article</subject>
21:                 </subj-group>
22:             </article-categories>
23:             <title-group>
24:                 <article-title>PERCEPCIONES DE PERSONAS DE SEXO MASCULINO HOMOSEXUALES QUE VIVEN CON VIH SOBRE LA PATERNIDAD</article-title>
25:                 <trans-title-group xml:lang="en">
26:                     <trans-title>PERCEPTIONS OF MALE HOMOSEXUAL PEOPLE LIVING WITH HIV ABOUT PATERNITY</trans-title>
27:                 </trans-title-group>
28:             </title-group>
29:             <contrib-group>
30:                 <contrib contrib-type="author">
31:                     <contrib-id contrib-id-type="orcid">https://orcid.org/0000-0001-7639-3531</contrib-id>
32:                     <name>
33:                         <surname>Rojas-Cáceres</surname>
34:                         <given-names>Camila</given-names>
35:                     </name>
36:                     <xref ref-type="aff" rid="aff1"/>
37:                     <xref ref-type="corresp" rid="cor1">*</xref>
38:                     <email>crojas293@uchile.cl</email>
39:                 </contrib>
40:                 <contrib contrib-type="author">
41:                     <contrib-id contrib-id-type="orcid">https://orcid.org/0009-0008-1977-7617</contrib-id>
42:                     <name>
43:                         <surname>Oyarzún-Pizarro</surname>
44:                         <given-names>Gabriela</given-names>
45:                     </name>
46:                     <xref ref-type="aff" rid="aff1"/>
47:                 </contrib>
48:                 <contrib contrib-type="author">
49:                     <contrib-id contrib-id-type="orcid">https://orcid.org/0009-0001-2347-6509</contrib-id>
50:                     <name>
51:                         <surname>Ozimisa-Martínez</surname>
52:                         <given-names>Lorena</given-names>
53:                     </name>
54:                     <xref ref-type="aff" rid="aff1"/>
55:                 </contrib>
56:                 <contrib contrib-type="author">
57:                     <contrib-id contrib-id-type="orcid">https://orcid.org/0009-0009-7319-5391</contrib-id>
58:                     <name>
59:                         <surname>Caro-Vargas</surname>
60:                         <given-names>Claudia</given-names>
61:                     </name>
62:                     <xref ref-type="aff" rid="aff2"/>
63:                 </contrib>
64:             </contrib-group>
65:             <aff id="aff1">
66:                 <label>1</label>
67:                 <institution content-type="original">Universidad de Chile</institution>
68:                 <institution content-type="orgname">Universidad de Chile</institution>
69:                 <country country="CL">Chile</country>
70:             </aff>
71:             <aff id="aff2">
72:                 <label>2</label>
73:                 <institution content-type="original">Hospital San Borja Arriarán</institution>
74:                 <institution content-type="orgname">Hospital San Borja Arriarán</institution>
75:                 <country country="CL">Chile</country>
76:             </aff>
77:             <author-notes>
78:                 <corresp id="cor1">
79:                     <label>*</label>Correspondencia: <email>crojas293@uchile.cl</email>
80:                 </corresp>
81:                 <fn fn-type="conflict">
82:                     <p>Los autores declaran no tener conflicto de intereses</p>
83:                 </fn>
84:             </author-notes>
85:             <pub-date pub-type="epub">
86:                 <day>21</day>
87:                 <month>01</month>
88:                 <year>2026</year>
89:             </pub-date>
90:             <volume>1</volume>
91:             <issue>1</issue>
92:             <fpage>13</fpage>
93:             <lpage>21</lpage>
94:             <history>
95:                 <date date-type="received" iso-8601-date="2025-05-29">
96:                     <day>29</day>
97:                     <month>05</month>
98:                     <year>2025</year>
99:                 </date>
100:                 <date date-type="accepted" iso-8601-date="2025-11-15">
101:                     <day>15</day>
102:                     <month>11</month>
103:                     <year>2025</year>
104:                 </date>
105:             </history>
106:             <permissions>
107:                 <license license-type="open-access" xlink:href="https://revistas.uv.cl/index.php/matroneria/derechos-autor">
108:                     <license-p>CC (BY-NC-SA) 4.0 Internacional</license-p>
109:                 </license>
110:             </permissions>
111:             <abstract>
112:                 <title>Resumen</title>
113:                 <p>Objetivo: describir las percepciones sobre la paternidad de personas de sexo masculino homosexuales que viven con VIH, en base a un estudio realizado en la Unidad de Infectología del Hospital Clínico San Borja Arriarán de Santiago de Chile, en 2024. Material y método: investigación cualitativa descriptiva de paradigma fenomenológico, que usó un muestreo no probabilístico opinático y muestra de sujetos-tipo, con un tamaño muestral definido por saturación de datos. Se realizaron doce entrevistas individuales semiestructuradas y un análisis narrativo de datos, con categorías apriorísticas. Se utilizó Atlas.ti® como herramienta de apoyo para análisis. Resultados: los hallazgos se dividieron en barreras y facilitadores, fortalezas y vivencias en torno al ejercicio de la paternidad de la muestra. Se encontraron barreras relacionadas al diagnóstico y otras que son transversales en la sociedad. Por otro lado, se identificó la atención en salud integral como facilitador para ejercer la paternidad, también, se reconoció como fortaleza la transmisión de conocimientos a los hijos. Por último, en vivencias, se señaló al diagnóstico como factor que repercutió en la decisión de ser padre, así como también a la orientación sexual. Conclusión: las percepciones de los participantes en torno al ejercicio de la paternidad fueron diversas y en general positiva</p>
114:             </abstract>
115:             <trans-abstract xml:lang="en">
116:                 <title>Abstract</title>
117:                 <p>Objective: describe the perceptions of homosexual men living with HIV regarding fatherhood in the Infectious Diseases Unit of the San Borja Arriarán Clinical Hospital in 2024. Methodology: descriptive qualitative research using a phenomenological paradigm, using non-probability opinion-based sampling and a sample of typical subjects, with a sample size based on data saturation. Twelve individual semi-structured interviews were conducted, along with a narrative data analysis using a priori categories. Atlas.ti® was used as the analysis tool. Results: results were divided into barriers and facilitators, strengths, and experiences related to fatherhood in the sample. Barriers related to diagnosis and others that are transversal to society were found. Furthermore, comprehensive healthcare was identified as a facilitator for fatherhood, also the transmission of knowledge to children was recognized as a strength. Finally, regarding their experiences it was pointed out that the diagnosis had an impact on their decision to become a parent, as well as the sexual orientation. Conclusion: the perceptions of the participants regarding paternity were diverse and mostly positive, except for the barriers mentioned before, which were considered as decisive factors when becoming parents.</p>
118:             </trans-abstract>
119:             <kwd-group xml:lang="es">
120:                 <kwd>paternidad</kwd>
121:                 <kwd>VIH</kwd>
122:                 <kwd>homosexualidad</kwd>
123:             </kwd-group>
124:             <kwd-group xml:lang="en">
125:                 <kwd>paternity</kwd>
126:                 <kwd>HIV</kwd>
127:                 <kwd>homosexuality</kwd>
128:             </kwd-group>
129:             <counts>
130:                 <fig-count count="2"/>
131:                 <table-count count="2"/>
132:                 <ref-count count="43"/>
133:                 <page-count count="9"/>
134:             </counts>
135:         </article-meta>
136:     </front>
137:     <body>
138:         <sec sec-type="intro">
139:             <title>Introducción</title>
140:             <p>Según la Organización Mundial de la Salud (OMS), el Virus de la Inmunodeficiencia Humana (VIH) constituye un problema de salud pública a nivel mundial, persistiendo su contagio al día de hoy en todos los países (OMS, 2023).</p>
141:             <p>En Chile se ha mostrado una tendencia al alza de contagios en los últimos años. En 2022 se contabilizaron unas 83 mil personas viviendo con VIH, concentrándose la mayoría de los casos en la región Metropolitana (Instituto de Salud Pública, 2023; ONUSIDA, 2022a). En el periodo 2010-2022, la distribución por sexo de contagios fue de 84,2% de hombres versus 15% de mujeres (Instituto de Salud Pública, 2023). Según cifras, los contagios en hombres ocurrieron a través de relaciones sexuales heterosexuales en un 16,4% y en homosexuales en un 53% (Ministerio de Salud, 2021).</p>
142:             <p>En relación con esta tendencia, en otros países de Latinoamérica se ha observado que existen diversos factores que propician la exposición de hombres a las ITS y VIH, particularmente el tener sexo con otros hombres <xref ref-type="bibr" rid="ref3">(Brignol et al., 2015)</xref>. Con respecto a lo anterior, en Argentina se realizó un estudio en varones homosexuales con VIH, quienes relataron haber sido discriminados tanto por su diagnóstico como por su orientación sexual, manifestando esto como una “doble discriminación” <xref ref-type="bibr" rid="ref36">(Radusky &amp; Mikulic, 2019)</xref>.</p>
143:             <p>En un estudio realizado en Chile se describe la discriminación del padre homosexual. Entre las vivencias descritas destaca el hecho de enfrentar estereotipos heteronormativos que sitúan a la mujer como quien asume el rol de cuidado y crianza y, por otro lado, el tener que proteger o velar por su familia ante situaciones de homofobia. De los participantes, quienes se convirtieron en padres estando en relaciones heterosexuales, visualizaban a la homosexualidad y paternidad como conceptos incompatibles, pues percibían la concepción de un hijo o hija en el marco de una pareja homosexual como algo difícil y que se debe buscar activamente, mediante la adopción o inseminación artificial <xref ref-type="bibr" rid="ref15">(Herrera et al., 2018)</xref>.</p>
144:             <p>Ahora, en relación a la paternidad de hombres homosexuales que viven con VIH, otro estudio realizado en Brasil analizó los factores relacionados a la intención de ser padre en hombres hetero y homosexuales. Entre los resultados se destaca que quienes manifestaron un mayor anhelo de ser padre fueron hombres que se encontraban hace más de tres años en terapia antirretroviral, por lo que se concluye que el contagio podría retrasar el deseo de tener hijos, mas no erradicarlo. Este estudio, a pesar de incluir a varones homosexuales, no tenía como objetivo analizar esta arista, por lo que sus conclusiones apuntan a la totalidad de la muestra <xref ref-type="bibr" rid="ref7">(da Silveira Reis et al., 2015)</xref>.</p>
145:             <p>Según lo expuesto, y considerando la falta de literatura nacional e internacional, resulta relevante la realización de un estudio enfocado en personas de sexo masculino, homosexuales y con un diagnóstico de VIH en Chile, específicamente en la región Metropolitana, ya que en este territorio se concentran la mayoría de casos del país (Instituto de Salud Pública, 2023). Es por esto que el objetivo de esta investigación es describir la percepción de personas del sexo masculino y homosexuales que viven con VIH en torno al ejercicio de la paternidad, considerando el abordaje de vivencias, barreras y facilitadores, fortalezas e impacto del diagnóstico en su deseo de ser padres y a partir de los resultados obtenidos, poder tener una visión más amplia en este tema, que permita aportar al conocimiento existente.</p>
146:         </sec>
147:         <sec sec-type="methods">
148:             <title>Material y método</title>
149:             <p>Esta investigación se llevó a cabo en la Unidad de Infectología del Hospital Clínico San Borja Arriarán (HCSBA), desde junio hasta octubre de 2024, utilizando la metodología cualitativa descriptiva <xref ref-type="bibr" rid="ref14">(Hernández Sampieri et al., 1991</xref>; <xref ref-type="bibr" rid="ref40">Sandelowski, 2000)</xref> y un paradigma fenomenológico debido a que se indagó en las percepciones y experiencias de los sujetos de estudio <xref ref-type="bibr" rid="ref39">(Vásquez et al., 2011)</xref>. Según Husserl, la fenomenología se basa en el análisis de las experiencias y vivencias de los sujetos, enfatizando en la subjetividad y en la intersubjetividad <xref ref-type="bibr" rid="ref17">(Husserl, 2011)</xref>.</p>
150:             <p>El universo del estudio correspondió a 5.399 usuarios que se controlaron en esa unidad del HCSBA. En relación al tamaño muestral, a priori se estimó un número de doce entrevistas semiestructuradas a realizar, las que, según la literatura, es la cifra en la que la mayoría de los estudios cualitativos alcanzan la saturación de datos <xref ref-type="bibr" rid="ref28">(Morse, 1995)</xref>, definida ésta como el momento donde las entrevistas ya no aportan nuevos discursos o información adicional <xref ref-type="bibr" rid="ref13">(Hennink &amp; Kaiser, 2022)</xref>.</p>
151:             <p>En su desarrollo se emplearon los siguientes criterios de inclusión: individuos de sexo masculino con un diagnóstico VIH positivo, sin importar la etapa y tiempo de diagnóstico, mayores de 18 años y que se controlaran en la Unidad de Infectología del HCSBA. Asimismo, se consideró como criterio de exclusión el no hablar español. Cabe destacar que ser homosexual no correspondía a un criterio de inclusión, sin embargo, la totalidad de participantes hallados se identificaban con esta orientación sexual.</p>
152:             <p>El muestreo con el que se trabajó fue no probabilístico de tipo opinático <xref ref-type="bibr" rid="ref14">(Hernández Sampieri et al., 1991)</xref>, ya que al seleccionar los sujetos de estudio se utilizaron criterios de factibilidad a conveniencia de las investigadoras, tales como facilidad de contacto y accesibilidad <xref ref-type="bibr" rid="ref39">(Vásquez et al., 2011)</xref>. En lo específico, se utilizó una muestra de sujetos-tipos <xref ref-type="bibr" rid="ref14">(Hernández Sampieri et al., 1991)</xref>.</p>
153:             <p>Asimismo, se realizó un análisis narrativo de los datos, ya que este busca describir lo que las personas dicen, cómo y por qué y así darles una voz, con el fin de otorgar un significado a su experiencia <xref ref-type="bibr" rid="ref12">(Gibbs, 2012)</xref>. Se aplicaron los criterios de rigor y calidad de la investigación cualitativa según Guba y Lincoln: credibilidad, confirmación mediante la transcripción apegada a la grabación de las entrevistas <xref ref-type="bibr" rid="ref22">(Lincoln &amp; Guba, 1985)</xref> y triangulación de investigadores <xref ref-type="bibr" rid="ref4">(Castillo &amp; Vásquez, 2003</xref>; <xref ref-type="bibr" rid="ref10">Erazo Jiménez, 2011</xref>; <xref ref-type="bibr" rid="ref22">Lincoln &amp; Guba, 1985</xref>; <xref ref-type="bibr" rid="ref29">Okuda Benavides &amp; Gómez-Restrepo, 2005)</xref>.</p>
154:             <p>La totalidad de categorías de análisis se definieron de forma apriorística, no hubo hallazgos de categorías emergentes en los resultados. A continuación, se definen:</p>
155:             <table-wrap id="t1">
156:                 <label>Tabla 1</label>
157:                 <caption>
158:                     <title>Categorías de análisis / Categories of analysis</title>
159:                 </caption>
160:                 <table frame="hsides" rules="groups">
161:                     <thead>
162:                         <tr>
163:                             <th>Nombre categoría</th>
164:                             <th>Clasificación</th>
165:                             <th>Definición</th>
166:                         </tr>
167:                     </thead>
168:                     <tbody>
169:                         <tr>
170:                             <td>Barreras y facilitadores en torno al ejercicio de la paternidad de personas de sexo masculino homosexuales que viven con VIH</td>
171:                             <td>Apriorística</td>
172:                             <td>Factores que impiden o complican el ejercicio de la paternidad de personas de sexo masculino, homosexuales, que viven con VIH (autoría propia), se consideran barreras económicas, biológicas, culturales y clínicas (Herrera et al., 2018; Vergês H. et al., 2019). Factores que ayudan o favorecen el ejercicio de la paternidad de personas de sexo masculino, homosexuales, que viven con VIH (autoría propia).</td>
173:                         </tr>
174:                         <tr>
175:                             <td>Fortalezas en torno al ejercicio de la paternidad de personas de sexo masculino homosexuales que viven con VIH</td>
176:                             <td>Apriorística</td>
177:                             <td>Factores positivos que se perciben en el ejercicio de la paternidad de personas de sexo masculino, homosexuales, que viven con VIH (autoría propia), se consideran fortalezas tales como personales, económicas, culturales y clínicas (da Silveira Reis et al., 2015)</td>
178:                         </tr>
179:                         <tr>
180:                             <td>Vivencias en relación a la paternidad de personas de sexo masculino homosexuales que viven con VIH</td>
181:                             <td>Apriorística</td>
182:                             <td>Sentimientos, deseos y experiencias en torno al ejercicio de la paternidad (Vergês H. et al., 2019)</td>
183:                         </tr>
184:                     </tbody>
185:                 </table>
186:             </table-wrap>
187:             <p>Con respecto al análisis de datos, se utilizó Atlas.ti® como un programa de apoyo para este proceso.</p>
188:             <p>Se realizaron 12 entrevistas individuales semiestructuradas <xref ref-type="bibr" rid="ref9">(Díaz-Bravo et al., 2013)</xref> previo a una validación de expertos (Fig. 1), donde participaron 5 personas con magíster en salud pública y experticia en VIH, quienes entregaron puntajes asociados a los criterios de validación en un instrumento ya trabajado. Todas las entrevistas se llevaron a cabo en un box de la unidad de infectología del HCSBA el mismo día del control de los usuarios, que fueron contactados en sala y aceptaron de forma voluntaria su participación en el estudio. Las entrevistas tuvieron una duración aproximada de 25 minutos, fueron dirigidas por ambas investigadoras principales y grabadas en un dispositivo que se utilizó exclusivamente para esta investigación.</p>
189:             <fig id="f1">
190:                 <label>Figura 1</label>
191:                 <caption>
192:                     <title>Pauta de entrevista / Interview guideline</title>
193:                 </caption>
194:                 <graphic mimetype="image" xlink:href="imagen_1.jpeg"/>
195:             </fig>
196:             <p>Este estudio fue realizado de acuerdo con la Asociación Médica Mundial y la Declaración de Helsinki (Asociación Médica Mundial, s. f.). Se encuentra aprobado por el Comité Ético del Servicio de Salud Metropolitano Central y por el Comité Ético Científico del HCSBA.</p>
197:             <p>Todas las personas que participaron de esta investigación firmaron un documento físico de consentimiento informado, con todas las consideraciones de su participación previo a la entrevista, además se resolvieron dudas.</p>
198:             <p>Por otro lado, se aseguró la confidencialidad de los datos a través del uso de un código de identificación, formado por la inicial del primer nombre y dos apellidos, fecha de nacimiento, los tres últimos dígitos del RUT y el dígito verificador <xref ref-type="bibr" rid="ref24">(Ministerio de Salud, 2009)</xref>, bajo el cual se almacenó la transcripción de la entrevista en un solo dispositivo electrónico, en la aplicación de Word®, teniendo acceso las tres investigadoras durante el período de un año desde la finalización del estudio.</p>
199:         </sec>
200:         <sec sec-type="results">
201:             <title>Resultados</title>
202:             <table-wrap id="t2">
203:                 <label>Tabla 2</label>
204:                 <caption>
205:                     <title>Caracterización de la muestra / Sample characterization</title>
206:                 </caption>
207:                 <table frame="hsides" rules="groups">
208:                     <thead>
209:                         <tr>
210:                             <th>Identificación</th>
211:                             <th>Género</th>
212:                             <th>Edad</th>
213:                             <th>Ocupación</th>
214:                             <th>Año de diagnóstico</th>
215:                             <th>Diagnóstico en sistema público o privado</th>
216:                         </tr>
217:                     </thead>
218:                     <tbody>
219:                         <tr>
220:                             <td>Entrevistado 1 (E1)</td>
221:                             <td>Masculino</td>
222:                             <td>29</td>
223:                             <td>Ingeniero</td>
224:                             <td>2023</td>
225:                             <td>Privado</td>
226:                         </tr>
227:                         <tr>
228:                             <td>Entrevistado 2 (E2)</td>
229:                             <td>No binario</td>
230:                             <td>30</td>
231:                             <td>Garzón</td>
232:                             <td>2019</td>
233:                             <td>Dg realizado en otro país</td>
234:                         </tr>
235:                         <tr>
236:                             <td>Entrevistado 3 (E3)</td>
237:                             <td>Masculino</td>
238:                             <td>48</td>
239:                             <td>Artista</td>
240:                             <td>2002</td>
241:                             <td>Privado</td>
242:                         </tr>
243:                         <tr>
244:                             <td>Entrevistado 4 (E4)</td>
245:                             <td>Masculino</td>
246:                             <td>53</td>
247:                             <td>Cesante</td>
248:                             <td>2010</td>
249:                             <td>Público</td>
250:                         </tr>
251:                         <tr>
252:                             <td>Entrevistado 5 (E5)</td>
253:                             <td>Masculino</td>
254:                             <td>28</td>
255:                             <td>Encargado de local</td>
256:                             <td>2017</td>
257:                             <td>Privado</td>
258:                         </tr>
259:                         <tr>
260:                             <td>Entrevistado 6 (E6)</td>
261:                             <td>Masculino</td>
262:                             <td>57</td>
263:                             <td>Comerciante</td>
264:                             <td>2016</td>
265:                             <td>Público</td>
266:                         </tr>
267:                         <tr>
268:                             <td>Entrevistado 7 (E7)</td>
269:                             <td>Masculino</td>
270:                             <td>53</td>
271:                             <td>Contador</td>
272:                             <td>2001</td>
273:                             <td>Público</td>
274:                         </tr>
275:                         <tr>
276:                             <td>Entrevistado 8 (E8)</td>
277:                             <td>Masculino</td>
278:                             <td>43</td>
279:                             <td>Contador</td>
280:                             <td>2009</td>
281:                             <td>Privado</td>
282:                         </tr>
283:                         <tr>
284:                             <td>Entrevistado 9 (E9)</td>
285:                             <td>Masculino</td>
286:                             <td>30</td>
287:                             <td>Administrativo</td>
288:                             <td>2022</td>
289:                             <td>Privado</td>
290:                         </tr>
291:                         <tr>
292:                             <td>Entrevistado 10 (E10)</td>
293:                             <td>Masculino</td>
294:                             <td>39</td>
295:                             <td>Masoterapeuta</td>
296:                             <td>2016</td>
297:                             <td>Público</td>
298:                         </tr>
299:                         <tr>
300:                             <td>Entrevistado 11 (E11)</td>
301:                             <td>Masculino</td>
302:                             <td>50</td>
303:                             <td>Independiente</td>
304:                             <td>2001</td>
305:                             <td>Público</td>
306:                         </tr>
307:                         <tr>
308:                             <td>Entrevistado 12 (E12)</td>
309:                             <td>Masculino</td>
310:                             <td>35</td>
311:                             <td>Conserje</td>
312:                             <td>2019</td>
313:                             <td>Público</td>
314:                         </tr>
315:                     </tbody>
316:                 </table>
317:             </table-wrap>
318:             <sec>
319:                 <title>Vivencias en relación a la paternidad de personas de sexo masculino homosexuales que viven con VIH</title>
320:                 <p>Esta categoría se entiende como los deseos, sentimientos y experiencias en torno a ejercer la paternidad. Ninguno de los entrevistados es padre, sin embargo, existen algunos que desean serlo. Las razones para no ejercer la paternidad son heterogéneas: alrededor de la mitad coincidió en que el diagnóstico de VIH influyó, mientras que otros destacaron la orientación sexual, ya que consideraron que la homosexualidad constituye un impedimento para tener un/a hijo/a.</p>
321:                 <p>“…cuando yo me di cuenta de que era gay, me di cuenta de que ya no me podía casar, no podía tener hijos y que solamente eso” (E4)</p>
322:                 earlier running meant the file was overwritten twice. Since the original file isn't in git, I should reconstruct it from the read outputs.
322:                 <p>Quienes vieron afectado su deseo de ser padres, tras recibir el diagnóstico, argumentaron como razones la carga emocional que conlleva eso, el pensamiento de una disminución de la calidad de vida, la posibilidad de que su hijo/a fuese discriminado y el riesgo de transmitir el virus durante la concepción. Refieren que se debe a la falta de información acerca de formas seguras de concebir y/o al temor de que el medicamento dejase de funcionar.</p>
323:                 <p>“… de cierta forma el medicamento es efectivo, pero siento que, si en algún momento dejara de funcionar yo y tener un hijo con VIH pues, para mí sería como que no quiero eso para él…” (E1)</p>
324:                 <p>“... sabiendo que uno tiene VIH, ¿cómo se va a inseminar a una mujer en este caso? para también va a correr riesgo ella, entonces como que uno se empieza a cuestionar desde la ignorancia, pues la verdad que jamás me he puesto averiguar…” (E8)</p>
325:                 <p>Se generó consenso en los discursos en cuanto a los sentimientos que surgen a raíz de la decisión de ser o no ser padre, donde todos describieron estar satisfechos con ello.</p>
326:                 <p>Hubo opiniones discordantes en cuanto a las vías para convertirse en padre. Por un lado, se planteó la adopción, privilegiando el vínculo afectivo por sobre la genética y, por otro lado, la inseminación artificial, por el deseo de tener hijos biológicos y por las dificultades que ellos consideran que conlleva el proceso de adopción.</p>
327:             </sec>
328:             <sec>
329:                 <title>Barreras y facilitadores en torno al ejercicio de la paternidad de personas de sexo masculino homosexuales que viven con VIH</title>
330:                 <p>Esta categoría se refiere a las barreras en torno al ejercicio de la paternidad en esta población, definidas de forma apriorística como barreras sociales, económicas, biológicas y de redes de apoyo. Además, surgieron otras no consideradas anteriormente.</p>
331:                 <p>Los resultados son heterogéneos, en algunos casos los participantes no percibieron barreras, sin embargo, luego del análisis de datos, se encontraron verbatims que reflejan de manera implícita aquellos factores que impidieron el ejercicio de su paternidad.</p>
332:                 <p>“Es que yo siempre supe que yo no iba a ser papá.... yo siempre dije que soy homosexual, no podría tener hijos, porque no corresponde, ¿para qué?” (E7)</p>
333:                 <p>En este caso, el entrevistado no identifica la barrera por orientación sexual, sin embargo, dentro de su relato la expresa implícitamente.</p>
334:                 <p>Los resultados de esta categoría fueron divididos en las barreras que se relacionan directamente con el diagnóstico de VIH positivo y las que aluden a la paternidad por sí sola (Fig. 2).</p>
335:                 <fig id="f2">
336:                     <label>Figura 2</label>
337:                     <caption>
338:                         <title>Barreras en torno al ejercicio de la paternidad de personas de sexo masculino homosexuales que viven con VIH / Barriers to parenthood for male homosexual people living with HIV</title>
339:                     </caption>
340:                     <graphic mimetype="image" xlink:href="imagen_2.jpeg"/>
341:                 </fig>
342:                 <p>Adentrándonos en los discursos, en cuanto al ámbito social, se refirieron prejuicios, ignorancia y rechazo por parte de la sociedad, así surge como barrera el temor a ser discriminado, ya sea por ejercer la paternidad siendo un hombre homosexual o por vivir con VIH.</p>
343:                 <p>“Es que yo creo que si yo tuviera un hijo nunca le diría que tengo VIH, porque todo los niños lo transmiten, entonces ponte que lo diga en el colegio, o si llega a salir, puede alguien discriminar…” (E1)</p>
344:                 <p>Las barreras biológicas y por orientación sexual se vieron evidenciadas implícitamente en los relatos de participantes que decidieron no ser padres netamente por su diagnóstico de VIH o ser homosexual, como se explicó en el apartado de “Vivencias en torno al ejercicio de la paternidad de personas de sexo masculino homosexuales que viven con VIH”.</p>
345:                 <p>Algunos entrevistados concluyeron que no existen barreras siempre y cuando su diagnóstico no fuese conocido por los demás, ya que refieren que es un tema íntimo e innecesario de hacer público, por lo que no debería ser una barrera.</p>
346:                 <p>“sí hay una barrera social al llamar al que yo cuente y lo hable socialmente: tengo VIH y voy a ser padre y quiero ser padre, eso sí va a haber una barrera social importante, pero, ¿es importante que también el resto se entere de mis, de mis planes personales previos? creo que no y aunque engendrar a un hijo ¿por qué tengo que contarle al resto que yo tengo VIH?...” (E3)</p>
347:                 <p>En la esfera económica, se plantea a la estabilidad económica como un requisito para ejercer la paternidad. De esta forma, los entrevistados señalaron la postergación de ser padre por estar en búsqueda de un mejor pasar económico.</p>
348:                 <p>“yo creo que el tema económico es lo que siempre más frena, porque igual está difícil la cosa y para tener un niño y tenerlo de mala calidad, no es la idea” (E11)</p>
349:                 <p>En cuanto a las barreras asociadas a las redes de apoyo, algunos participantes lo consideran necesario, argumentando que tener un hijo/a es un trabajo de dos personas.</p>
350:                 <p>Luego, en las barreras autoimpuestas, estas se plantean como limitaciones personales, sin la existencia de barreras externas para convertirse en padre homosexual viviendo con VIH.</p>
351:                 <p>“porque realmente las únicas barreras somos nosotros, como nosotros nos ponemos: “no, no puedo” entonces no puedes” (E2)</p>
352:                 <p>Con respecto a los facilitadores en torno al ejercicio de la paternidad, son factores que propician la toma de decisiones en salud sexual y reproductiva. Se encontró una buena percepción de la atención en salud recibida entre los entrevistados, destacando la consejería, medicamentos, seguimiento y contención emocional. Lo anterior los ayuda a sobrellevar los sentimientos negativos que surgen al recibir el diagnóstico de VIH. Este discurso aparece de manera espontánea durante las entrevistas.</p>
353:                 <p>“... El área de salud pública aquí es un 7, aquí los profesionales te atienden súper bien, te tienen mucha paciencia y sigo las indicaciones al pie de la letra, más encima me lo dan gratis… ese lado positivo me tranquilizó, sé que puedo vivir como cualquier persona y que no voy mañana a enfermar, ni voy a morir, ¿no?” (E4)</p>
354:             </sec>
355:             <sec>
356:                <title>Fortalezas en torno al ejercicio de la paternidad de personas de sexo masculino homosexuales que viven con VIH</title>
357:                 <p>Esta categoría se entiende como los aspectos positivos considerados por los participantes en relación a su vivencia y ejercicio de la paternidad viviendo con VIH.</p>
358:                 <p>La gran parte de los discursos coincidieron en la existencia de fortalezas al ejercer la paternidad con VIH, como la posibilidad de transmitir conocimientos y aprendizajes de autocuidado y educación sexual, en base a lo que han vivido.</p>
359:                 <p>“...Sí, porque considero yo que si yo fuera un padre con VIH, este, a mi hijo obviamente le... como que le inculco más cuidarse, más protegerse” (E12)</p>
360:                 <p>Por otro lado, surgió la idea de que los padres que viven con VIH podrían entregar más cariño, amor, respeto y una educación libre de prejuicios, debido a tener vivencias únicas por su diagnóstico.</p>
361:                 <p>También surgió un discurso en menor proporción, el cual apunta como fortaleza de ser padre viviendo con VIH el desarrollo del autocuidado.</p>
362:                 <p>“... un hijo a lo mejor le podría gatillar el: “no, puta, es que tengo un hijo, ahora me voy, me tengo que cuidar, tengo un motivo, tengo, tengo otra responsabilidad” entonces a lo mejor eso podría gatillarlo a empezar a cuidarse él…” (E8)</p>
363:                 <p>Por el contrario, con mucha menos frecuencia, existió el discurso en donde no se encontraron fortalezas de ser padre viviendo con VIH.</p>
364:                 <p>“Yo creo que es igual, porque se supone que la persona con VIH va a tener sus precauciones en todo y un papá normal, o sea que no contrae el virus, también lleva una vida normal…” (E9)</p>
365:             </sec>
366:         </sec>
367:         <sec sec-type="discussion">
368:             <title>Discusión</title>
369:             <p>La percepción de los participantes se verificó como heterogénea. Algunos no quisieron ser padres tras recibir su diagnóstico y otros ya lo tenían decidido por su orientación sexual u otros factores. El primer grupo revela una realidad similar a la encontrada en estudios de Brasil, Estados Unidos y Reino Unido, enfocados en la percepción de paternidad con VIH de hombres en parejas heterosexuales serodiscordantes, donde la mayoría sintió preocupación y culpa de exponer a sus hijos/as a una situación de vulnerabilidad de contagio <xref ref-type="bibr" rid="ref21">(Langendorf et al., 2020</xref>; <xref ref-type="bibr" rid="ref35">Pralat, Burns, et al., 2021</xref>; <xref ref-type="bibr" rid="ref38">Rodríguez et al., 2017</xref>; <xref ref-type="bibr" rid="ref41">Sastre et al., 2015</xref>; <xref ref-type="bibr" rid="ref42">Siegel et al., 2018)</xref>, esto debido a la falta de información en cuanto a formas seguras de concebir <xref ref-type="bibr" rid="ref34">(Pralat, Anderson, et al., 2021</xref>; <xref ref-type="bibr" rid="ref38">Rodríguez et al., 2017</xref>; <xref ref-type="bibr" rid="ref43">Weber et al., 2017)</xref>. En cuanto al segundo grupo, sus relatos se diferencian de lo encontrado en un estudio de México, donde se observa que la idea de convertirse en madre resulta inconcebible y se considera como un deseo negativo e irresponsable, debido a la posibilidad de transmisión del virus a un futuro hijo/a <xref ref-type="bibr" rid="ref42">(Viñas Pérez et al., 2017)</xref>.</p>
370:             <p>Como se dijo, se percibe la homosexualidad como una barrera para ser padre, siendo similar a un estudio de Colombia, donde destaca que una cantidad considerable de esta población decide no ejercer su paternidad por el estigma social, el cual consideran que es mayor para los hombres homosexuales <xref ref-type="bibr" rid="ref37">(Restrepo Pineda &amp; Jaramillo, 2020)</xref>, influenciado por ideas religiosas y prejuicios <xref ref-type="bibr" rid="ref33">(Pantoja Bohórquez et al., s. f.)</xref>, dentro de ellos, la idea de que el cuidado de los hijos es un trabajo de la mujer <xref ref-type="bibr" rid="ref5">(Chinyandura et al., 2024</xref>; <xref ref-type="bibr" rid="ref15">Herrera et al., 2018)</xref>. Por estas mismas razones, algunos miembros de la comunidad que decidieron ser padres/madres optan por ocultar sus relaciones afectivas <xref ref-type="bibr" rid="ref19">(Jaramillo-Jaramillo &amp; Restrepo-Pineda, 2019)</xref>. Se puede observar que las vivencias y percepciones en torno a ser padre con VIH son diferentes de acuerdo a la orientación sexual, ya que los hombres homosexuales cargan con un estigma adicional asociado a su sexualidad.</p>
371:             <p>Como barrera social surgió el miedo a ser discriminado, lo que se asemeja con estudios de Argentina y Reino Unido, que incluyeron en su muestra a varones homosexuales viviendo con VIH, encontrándose múltiples relatos de experiencias de “doble discriminación”, tanto por su orientación sexual y por su diagnóstico, lo que llevó a algunos de sus participantes a no revelarlo a su entorno <xref ref-type="bibr" rid="ref37">(Rai et al., 2018)</xref>. Lo anterior también se asemeja al presente estudio en los participantes que relatan no percibir barreras en torno al diagnóstico, siempre y cuando no lo revelen con las demás personas <xref ref-type="bibr" rid="ref36">(Radusky &amp; Mikulic, 2019)</xref>.</p>
372:             <p>Las barreras económicas y de redes de apoyo son transversales en la población. Esto se ve reflejado en dos investigaciones realizadas en mujeres en Chile, en las cuales se obtuvo que postergan su maternidad hasta alcanzar ciertas metas laborales, educativas y una autonomía económica, además de la falta de una red de apoyo <xref ref-type="bibr" rid="ref8">(Díaz, 2023</xref>; <xref ref-type="bibr" rid="ref44">Yopo Díaz, 2021)</xref>. Así, existe la percepción de barreras para ejercer la paternidad y maternidad independiente del género, orientación sexual y condición serológica, mientras que hay otras, que por su naturaleza, están relacionadas directamente al diagnóstico de VIH.</p>
373:             <p>Según los participantes, la atención recibida en la unidad de infectología genera un cambio en su percepción en torno al VIH, adoptando una actitud positiva y de tranquilidad, que promueve la proyección a futuro, constituyendo así un facilitador. Esto se asemeja a un estudio de Brasil, en personas que viven con VIH, donde mientras más satisfechos están con la atención en salud recibida, mejor es su percepción de calidad de vida <xref ref-type="bibr" rid="ref16">(Hipolito et al., 2017)</xref>. Siguiendo la misma línea, en estudios de Perú y Cuba a poblaciones con un diagnóstico de VIH surge como resultado la importancia del cuidado en salud en relación a los sentimientos de esperanza de los participantes y cómo afecta de forma positiva en su tratamiento <xref ref-type="bibr" rid="ref2">(Baca Chancafe et al., 2024</xref>; <xref ref-type="bibr" rid="ref23">Maiorana et al., 2024)</xref>. Por otro lado, en un estudio Chileno, dirigido a la atención en salud de personas de la comunidad LGBTQI+, se encontró una perspectiva diferente, ya que sus participantes manifestaron haber sido víctimas de discriminación, estigmas y malos tratos, esto porque la atención tenía un enfoque heteronormativo y que no consideraba sus necesidades <xref ref-type="bibr" rid="ref11">(Estay et al., 2020)</xref>. De esta forma, existen diversos estudios que avalan que una atención en salud integral y de buena calidad, mejora la actitud de los usuarios frente a su diagnóstico, es por esto que resulta fundamental trabajar y reforzar prácticas de buen trato al paciente en las unidades, así como también la formación profesional en materia de diversidad sexual <xref ref-type="bibr" rid="ref20">(Kyne et al., 2021)</xref>.</p>
374:             <p>Entre las fortalezas para ejercer la paternidad en esta población, se destacó la posibilidad de transmitir enseñanzas libres de prejuicios a sus hijos en base a sus vivencias, lo que es similar a un estudio Chileno, en donde los entrevistados plantean que tener un padre homosexual es beneficioso para sus hijos, pues los convierte en personas tolerantes, respetuosas y que valoran la diversidad por haberse criado en una familia “diferente”, lo que podría aplicar a cualquier tipo de diversificación familiar <xref ref-type="bibr" rid="ref15">(Herrera et al., 2018)</xref>.</p>
375:             <p>Se destaca como fortaleza del presente trabajo la realización de entrevistas semiestructuradas, ya que permitió que los participantes pudieran profundizar en sus experiencias, percepciones y así aportar riqueza al relato. Además, el instrumento de recolección de datos fue validado por un comité de expertos para asegurar que fuese atingente con el objetivo.</p>
376:             <p>La limitación del estudio apunta a la captación de personas en la sala de espera de la Unidad de Infectología del HCSBA. Los usuarios acudían al lugar citados a controles de salud, para abordar esto, se esperó a que los usuarios completaran su proceso de atención y se les entrevistó después.</p>
377:         </sec>
378:         <sec sec-type="conclusions">
379:             <title>Conclusiones</title>
380:             <p>Las percepciones sobre la paternidad de las personas de sexo masculino homosexuales que viven con VIH son heterogéneas, existiendo diversos factores que las llevan a no convertirse en padres. Entre los más influyentes figuran el diagnóstico de VIH positivo, ser homosexual, la existencia de estigmas sociales y estabilidad económica. Mientras que entre los factores positivos o fortalezas, los discursos son más homogéneos, destacando entre ellos la posibilidad de transmitir conocimientos y vivencias a sus hijos/as.</p>
381:             <p>Además, los resultados y la literatura internacional sugieren que una buena atención en salud aumenta la calidad de vida de los usuarios, por lo que, considerando que la población estudiada carga con estigmas adicionales y discriminación, resulta necesaria la entrega de una consejería integral en la atención en salud, informativa y que considere la formación profesional en diversidad sexual para empoderar a los usuarios.</p>
382:             <p>Los hallazgos sugieren seguir investigando a esta población en específico, debido al vacío existente en el conocimiento actual en la literatura nacional e internacional y al aporte que esto significaría en la atención al usuario.</p>
383:             <p>Se considera que investigaciones en esta materia serían un aporte a la profesión y a la formación debido a que la matronería cumple un rol fundamental en esta área. Es interesante considerar en la formación profesional la diversidad sexual y género, lo que permitirá brindar una atención respetuosa, centrada en la persona y que empodere a usuarios. También, abre diversas líneas de investigación, como la referente a las vías para convertirse en padre en esta muestra y el rol del personal de salud durante ese proceso.</p>
384:         </sec>
385:     </body>
386:     <back>
387:         <ack>
388:             <p>Agradecemos a quienes generosamente participaron en este estudio y lo hicieron posible y a la Unidad de Infectología del Hospital Clínico San Borja Arriarán por recibirnos.</p>
389:         </ack>
390:         <ref-list>
391:             <title>Referencias bibliográficas</title>
392:             <ref id="ref1">
393:                 <label>1</label>
394:                 <mixed-citation>Asociación Médica Mundial. (s. f.). Declaración de Helsinki de la Asociación Médica Mundial. https://www.wma.net/es/policies-post/declaracion-de-helsinki-de-la-amm-principios-eticos-para-las-investigaciones-medicas-en-seres-humanos/</mixed-citation>
395:             </ref>
396:             <ref id="ref2">
397:                 <label>2</label>
398:                 <mixed-citation>Baca Chancafe, J. M., Vega Ramírez, A. S., Díaz Manchay, R. J., Mogollón Torres, F. de M., Cervera Vallejos, M. F., &amp; Guerrero Quiroz, E. S. (2024). Nursing care from the perception of people with HIV/AIDS. Revista Cubana de Enfermería. https://www.researchgate.net/publication/383182433_Nursing_Care_from_the_Perception_of_People_with_HIVAids</mixed-citation>
399:             </ref>
400:             <ref id="ref3">
401:                 <label>3</label>
402:                 <mixed-citation>Brignol, S., Dourado, I., Amorim, L. D., &amp; Sansigolo Kerr, L. R. F. (2015). Vulnerability in the context of HIV and syphilis infection in a population of men who have sex with men (MSM) in Salvador, Bahia State, Brazil. Cadernos de Saúde Pública, 31(5), 1035–1048. https://doi.org/10.1590/0102-311X00178313</mixed-citation>
403:             </ref>
404:             <ref id="ref4">
405:                 <label>4</label>
406:                 <mixed-citation>Castillo, E., &amp; Vásquez, M. L. (2003). El rigor metodológico en la investigación cualitativa. Colomb Med, 34(3), 164–167.</mixed-citation>
407:             </ref>
408:             <ref id="ref5">
409:                 <label>5</label>
410:                 <mixed-citation>Chinyandura, C., Davies, N., Buthelezi, F., Jiyane, A., &amp; Rees, K. (2024). Using fatherhood to engage men in HIV services via maternal, neonatal and child health entry points in South Africa. PLoS ONE, 19(6). https://doi.org/10.1371/journal.pone.0296955</mixed-citation>
411:             </ref>
412:             <ref id="ref6">
413:                 <label>6</label>
410:                 <mixed-citation>Cohn, S. E., Haddad, L. B., Sheth, A. N., Hayford, C., Chmiel, J. S., Janulis, P. F., &amp; Schmandt, J. (2018). Parenting desires among individuals living with human immunodeficiency virus in the United States. Open Forum Infectious Diseases, 5(10). https://doi.org/10.1093/ofid/ofy232</mixed-citation>
415:             </ref>
416:             <ref id="ref7">
417:                 <label>7</label>
418:                 <mixed-citation>da Silveira Reis, C. B., Leite Araújo, M. A., Andrade, R. F. V., &amp; Miranda, A. E. B. (2015). Prevalence and factors associated with paternity intention among men living with HIV/AIDS in Fortaleza, Ceará. Texto &amp; Contexto - Enfermagem, 24(4), 1053–1060. https://doi.org/10.1590/0104-0707201500003560014</mixed-citation>
419:             </ref>
420:             <ref id="ref8">
421:                 <label>8</label>
422:                 <mixed-citation>Díaz, M. Y. (2023, diciembre 1). The postponement of motherhood in Chile: Between autonomy and precarity. Universum, 38(2), 591–616. https://doi.org/10.4067/s0718-23762023000200591</mixed-citation>
423:             </ref>
424:             <ref id="ref9">
425:                 <label>9</label>
426:                 <mixed-citation>Díaz-Bravo, L., Torruco-García, U., Martínez-Hernández, M., &amp; Varela-Ruiz, M. (2013). La entrevista, recurso flexible y dinámico. Investigación en Educación Médica, 2(7), 162–167. https://www.scielo.org.mx/pdf/iem/v2n7/v2n7a9.pdf</mixed-citation>
427:             </ref>
428:             <ref id="ref10">
429:                 <label>10</label>
430:                 <mixed-citation>Erazo Jiménez, M. S. (2011). Rigor científico en las prácticas de investigación cualitativa. Ciencia, Docencia y Tecnología, 42, 107–136. http://www.scielo.org.ar/scielo.php?script=sci_arttext&amp;pid=S1851-17162011000100004</mixed-citation>
431:             </ref>
432:             <ref id="ref11">
433:                 <label>11</label>
434:                 <mixed-citation>Estay, F., Valenzuela, A., &amp; Cartes, R. (2020). Health-care on LGBT+ people: Perspectives from the local community from Concepción. Revista Chilena de Obstetricia y Ginecología. https://www.researchgate.net/publication/344845853_Atencion_en_salud_de_personas_LGBT_Perspectivas_desde_la_comunidad_local_penquista</mixed-citation>
435:             </ref>
436:             <ref id="ref12">
437:                 <label>12</label>
438:                 <mixed-citation>Gibbs, G. (2012). El análisis de datos cualitativos en investigación cualitativa. Ediciones Morata S. L. https://www.digitaliapublishing.com/a/24050</mixed-citation>
439:             </ref>
440:             <ref id="ref13">
441:                 <label>13</label>
442:                 <mixed-citation>Hennink, M., &amp; Kaiser, B. N. (2022). Sample sizes for saturation in qualitative research: A systematic review of empirical tests. Social Science &amp; Medicine, 292. https://doi.org/10.1016/j.socscimed.2021.114523</mixed-citation>
443:             </ref>
444:             <ref id="ref14">
445:                 <label>14</label>
446:                 <mixed-citation>Hernández Sampieri, R., Fernández Collado, C., &amp; Baptista Lucio, P. (1991). Metodología de la investigación. McGraw-Hill. https://www.uv.mx/personal/cbustamante/files/2011/06/metodologia-de-la-investigaci%C3%83%C2%B3n_sampieri.pdf</mixed-citation>
447:             </ref>
448:             <ref id="ref15">
449:                 <label>15</label>
450:                 <mixed-citation>Herrera, F., Miranda, C., Pavicevic, Y., &amp; Sciaraffia, V. (2018). “Soy un papá súper normal”: Experiencias parentales de hombres gay en Chile. Polis. Revista Latinoamericana. http://journals.openedition.org/polis/15597</mixed-citation>
451:             </ref>
452:             <ref id="ref16">
453:                 <label>16</label>
454:                 <mixed-citation>Hipolito, R. L., Oliveira, D. C. de, Costa, T. L. da, Marques, S. C., Pereira, E. R., &amp; Gomes, A. M. T. (2017). Quality of life of people living with HIV/AIDS: Temporal, sociodemographic and perceived health relationship. Revista Latino-Americana de Enfermagem, 25. https://doi.org/10.1590/1518-8345.1258.2874</mixed-citation>
455:             </ref>
"""

# Strip line numbers and write
lines = []
for line in original_lines.splitlines():
    # Remove leading number and colon
    m = __import__('re').match(r'^\d+:\s', line)
    if m:
        lines.append(line[m.end():])
    else:
        lines.append(line)

with open('/Users/usuario/dev/XML-JATS-2/4975.xml', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("Restored original 4975.xml")
