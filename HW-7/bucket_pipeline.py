import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import re
import logging

logging.getLogger().setLevel(logging.INFO)

class LogElements(beam.DoFn):
    def process(self, element):
        logging.info(element)
        yield element

class ExtractLinks(beam.DoFn):
    def process(self, element):
        LINK_PATTERN = re.compile(r'<a\s+(?:[^>]*?\s+)?href="(\d+\.html)"', re.IGNORECASE)
        file_name, content = element
        links = LINK_PATTERN.findall(content)
        return [(file_name, link) for link in links]

def format_result(element):
    file, link_count = element
    return f'{file}: {link_count} links'

def run():
    # Define your pipeline options
    options = PipelineOptions(
        runner='DirectRunner',  # Change to 'DirectRunner' for local testing or DataflowRunner for prod
        project='ds-561-vanisinghal',
        temp_location='gs://hw-2-bucket-ds561/files',
        region='us-central1'
    )

    with beam.Pipeline(options=options) as pipeline:
        # Read files from Google Cloud Storage
        files_content = (
            pipeline 
            | 'ReadFiles' >> beam.io.ReadFromTextWithFilename('gs://hw-2-bucket-ds561/files/*')
            | 'ExtractLinks' >> beam.ParDo(ExtractLinks())
        )

        # Count outgoing links
        outgoing_links_count = (
            files_content
            | 'CountOutgoing' >> beam.combiners.Count.PerKey()
            | 'LogOutgoingCounts' >> beam.ParDo(LogElements())
            | 'FormatOutgoing' >> beam.Map(format_result)
            | 'GetTop5Outgoing' >> beam.transforms.combiners.Top.Of(5, key=lambda x: x[1])
            | 'WriteTopOutgoing' >> beam.io.WriteToText('gs://hw-2-bucket-ds561/files/output/local/top_outgoing')
        )

        # Count incoming links
        incoming_links_count = (
            files_content
            | 'MapToIncoming' >> beam.Map(lambda x: (x[1], x[0]))  # Swap to count incoming
            | 'CountIncoming' >> beam.combiners.Count.PerKey()
            | 'LogIncomingCounts' >> beam.ParDo(LogElements())
            | 'FormatIncoming' >> beam.Map(format_result)
            | 'GetTop5Incoming' >> beam.transforms.combiners.Top.Of(5, key=lambda x: x[1])
            | 'WriteTopIncoming' >> beam.io.WriteToText('gs://hw-2-bucket-ds561/files/output/local/top_incoming')
        )

if __name__ == '__main__':
    run()
